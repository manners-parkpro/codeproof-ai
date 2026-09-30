"""외부 지적을 가져온다 - **API 키가 필요 없는 확장 경로.**

포맷 어댑터(formats.py)가 있으면 어떤 도구든 리뷰어가 된다:
SARIF 계열(CodeQL · semgrep · Snyk · Trivy) 과 자기 JSON 을 내는 것(bandit) 둘 다.

[실측] bandit 은 SARIF 를 지원하지 않는다 - 「SARIF 면 다 된다」는 절반만 맞다.

그리고 에이전트 CLI(Codex CLI · Claude Code) 출력을 저장해 가져오면
**모델 축도 API 없이 열린다.**

🔴 다만 에이전트는 `ReviewerKind.AGENT` 다 - 툴 접근·다회 턴이 가능해서
   `MODEL_API` 와 층이 다르고, 섞어서 집계하면 안 된다.

디렉터리 규약:
    <root>/<sample_id>.json      한 샘플에 대한 지적
    <root>/<sample_id>.<run>.json  다회 실행이면 실행별로
    <root>/RUN.json              (선택) 실행기가 남긴 실행 기록

저장소에 싣는 모양은 **묶음**이다 - `RUN.json` + `findings.jsonl` (한 줄에 한 회차).
[실측] 60쌍 x 8회를 파일로 올리면 961개 - 당시 추적 파일 376개의 2.5배였다.
`unpack_runs()` 가 위 규약으로 되돌리므로 읽는 경로는 하나다.

## 🔴 매니페스트는 리뷰어가 신고한다 (E01)

[실측] 이 클래스에 `manifest_fields()` 가 없어서 에이전트 실행이
`effort="n/a(static)"` · `cache_policy="cold_only"` 로 기록될 뻔했다 -
러너의 기본값이 정적 도구용이기 때문이다. 에이전트는 effort 를 받고 돌았다.
→ `RUN.json` 이 있으면 거기 적힌 대로 신고한다. 없는데 확률적 층이면
  「모른다」고 신고한다 - 모르는 것을 정적 도구의 기본값으로 채우지 않는다.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from codeproof_ai.domain.reviewer import ReviewerKind, ReviewResult
from codeproof_ai.domain.run import ToolVersion
from codeproof_ai.llm.parse import parse_findings
from codeproof_ai.reviewers.formats import FORMATS

if TYPE_CHECKING:
    from pathlib import Path

    from codeproof_ai.domain.target import ReviewTarget

RUN_FILE = "RUN.json"
BUNDLE_FILE = "findings.jsonl"
_RUN_OUTPUT = re.compile(r"(?P<sid>.+)\.(?P<run>\d+)\.json")

# RUN.json 에서 설정 지문에 싣는 항목. 하나라도 다르면 다른 실행이다.
_SIGNED = (
    "model",
    "effort",
    "isolation",
    "permission",
    "instruction_hash",
    "prompt_hash",
    "schema_hash",
)


def pack_runs(root: Path) -> str:
    """실행기 출력(`<sample_id>.<run>.json`)을 한 줄에 한 회차씩 묶는다.

    🔴 결정적이다 - (샘플, 회차) 순서로 쓴다. 같은 출력이 같은 바이트가 되어야
       커밋 diff 가 실제 변화만 보인다.
    """
    rows = []
    for path in root.iterdir():
        if m := _RUN_OUTPUT.fullmatch(path.name):
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append((m["sid"], int(m["run"]), payload))
    rows.sort(key=lambda r: (r[0], r[1]))
    return "".join(
        json.dumps({"sample_id": sid, "run": run, "payload": payload}, ensure_ascii=False) + "\n"
        for sid, run, payload in rows
    )


def unpack_runs(bundle: Path, dest: Path) -> None:
    """묶음을 실행기 출력 모양으로 푼다 - import 와 **같은 경로**로 재생하려고."""
    for line in bundle.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        (dest / f"{row['sample_id']}.{row['run']}.json").write_text(
            json.dumps(row["payload"], ensure_ascii=False), encoding="utf-8"
        )


def read_run_record(root: Path) -> dict[str, Any] | None:
    """실행기가 남긴 기록. 없으면 None - 손으로 모은 출력일 수 있다."""
    path = root / RUN_FILE
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


class ImportedReviewer:
    """디스크에 저장된 지적을 재생한다.

    Args:
        root: `<sample_id>.json` 들이 있는 디렉터리.
        name: 리뷰어 이름. Finding.source 가 된다.
        identity: 재현용 식별자 (도구 버전 · 모델 ID · 커밋 등).
        kind: 🔴 층. 에이전트 출력을 가져오면 AGENT 로 둔다.
        fmt: FORMATS 의 키 — sarif · bandit · native.
    """

    def __init__(
        self,
        root: Path,
        *,
        name: str,
        identity: str,
        kind: ReviewerKind = ReviewerKind.IMPORTED,
        fmt: str = "sarif",
    ) -> None:
        if fmt not in FORMATS:
            msg = f"모르는 포맷: {fmt} ({' | '.join(sorted(FORMATS))})"
            raise ValueError(msg)
        self.root = root
        self.name = name
        self.identity = identity
        self.kind = kind
        self.fmt = fmt
        self._parser = FORMATS[fmt]
        self._cursor: dict[str, int] = {}
        self.run_record = read_run_record(root)
        self.rejected: list[str] = []
        """파서가 버린 지적 (제시되지 않은 파일 · 범위 밖 줄). 🔴 조용히 사라지지 않게 센다."""
        self.unrecognized: list[str] = []
        """포맷의 모양이 아닌 파일. 하나라도 있으면 그 실행의 숫자는 믿을 수 없다."""

    def config_signature(self) -> str:
        base = f"imported({self.name},fmt={self.fmt},kind={self.kind.value}"
        run = self.run_record
        if run is None:
            return base + ")"
        signed = ",".join(f"{k}={run.get(k)}" for k in _SIGNED)
        return f"{base},{signed})"

    @property
    def prompt_hash(self) -> str | None:
        run = self.run_record
        return str(run["prompt_hash"]) if run and run.get("prompt_hash") else None

    def manifest_fields(self) -> dict[str, str]:
        """🔴 러너가 짐작하지 않게 스스로 신고한다 (E01)."""
        run = self.run_record
        # 에이전트 CLI 는 캐시를 끌 수단을 주지 않는다 - 끈 척하지 않는다 (RunManifest).
        if run is not None and run.get("effort"):
            return {"effort": str(run["effort"]), "cache_policy": "uncontrolled"}
        if not self.kind.is_deterministic:
            return {"effort": "unknown", "cache_policy": "uncontrolled"}
        return {}

    def tool_versions(self) -> tuple[ToolVersion, ...]:
        run = self.run_record
        if run is None or not run.get("cli_version"):
            return ()
        tool = f"{run.get('agent', self.name)}-cli"
        return (ToolVersion(name=tool, version=str(run["cli_version"])),)

    def available_runs(self, sample_id: str) -> int:
        """이 샘플에 대해 0회차부터 **끊김 없이** 몇 회분이 저장돼 있는가.

        🔴 파일 개수를 세지 않는다. 실행 하나가 실패해 3회차가 비면(0,1,2,4...)
           개수는 7이지만 review() 는 3회차를 읽을 때 「지적 0건」을 낸다 -
           미측정이 미탐지로 둔갑한다. 이어진 앞부분만 센다.
        """
        n = 0
        while (self.root / f"{sample_id}.{n}.json").is_file():
            n += 1
        return n if n else int((self.root / f"{sample_id}.json").is_file())

    def review(self, target: ReviewTarget) -> ReviewResult:
        """저장된 다음 실행분을 낸다.

        다회분이 있으면 순서대로 소진한다 - 그래야 group_runs 가
        실제 실행 간 변동을 본다.
        """
        sid = target.target_id
        idx = self._cursor.get(sid, 0)
        self._cursor[sid] = idx + 1

        path = self.root / f"{sid}.{idx}.json"
        if not path.is_file():
            path = self.root / f"{sid}.json"
        if not path.is_file():
            # 🔴 없는 것은 "지적 0건" 이다. 예외로 실행을 멈추지 않는다.
            return ReviewResult(findings=(), raw={"_missing": str(path)})

        payload: Any = json.loads(path.read_text(encoding="utf-8"))
        if not self._parser.recognizes(payload):
            # 🔴 모르는 모양을 「지적 0건」으로 읽지 않는다 - 세어서 호출부가 거부하게 한다.
            self.unrecognized.append(str(path))
            return ReviewResult(findings=(), raw={"_unrecognized": str(path)})
        if self.fmt == "native" and isinstance(payload, dict):
            # native 파서는 버린 것을 `rejected` 에 남기는데 FindingFormat 은
            # 지적만 돌려준다 - 여기서 받아 둔다.
            outcome = parse_findings(payload, source=self.name, target=target)
            self.rejected.extend(f"{sid}#{idx}: {r}" for r in outcome.rejected)
            findings = outcome.findings
        else:
            findings = self._parser.parse(payload, self.name, target)
        return ReviewResult(
            findings=findings,
            raw={"_source": str(path), "_format": self.fmt},
        )
