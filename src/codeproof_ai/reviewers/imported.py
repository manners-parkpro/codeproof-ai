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
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from codeproof_ai.domain.reviewer import ReviewerKind, ReviewResult
from codeproof_ai.reviewers.formats import FORMATS

if TYPE_CHECKING:
    from pathlib import Path

    from codeproof_ai.domain.target import ReviewTarget

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

    def config_signature(self) -> str:
        return f"imported({self.name},fmt={self.fmt},kind={self.kind.value})"

    def available_runs(self, sample_id: str) -> int:
        """이 샘플에 대해 몇 회분이 저장돼 있는가."""
        n = len(list(self.root.glob(f"{sample_id}.*.json")))
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
        return ReviewResult(
            findings=self._parser.parse(payload, self.name, target),
            raw={"_source": str(path), "_format": self.fmt},
        )
