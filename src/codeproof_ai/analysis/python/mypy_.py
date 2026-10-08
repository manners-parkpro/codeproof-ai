"""mypy 어댑터.

🔴 `mypy.api.run` 을 쓰지 않는다 (CLAUDE.md C2).
   스트리밍이 불가능하고, 모듈 상태와 메모리를 워커에 누수시키며,
   run_dmypy 는 스레드 안전하지 않다. subprocess 가 격리·타임아웃·크래시 봉쇄를 준다.

컬럼 규약: mypy JSON 은 **0-based UTF-8 바이트**. 내부 규약은 0-based 문자.
⚠ 같은 mypy 실행이 텍스트 출력에서는 1-based 를 낸다 - JSON 만 쓴다.

🔴 격리가 두 겹이다:
   - `--config-file=/dev/null` : 호스트 프로젝트 설정 차단 (Ruff 의 --isolated 대응)
   - `--no-incremental` + `--cache-dir=/dev/null` : 증분 캐시 차단

   둘 다 없으면 같은 코퍼스가 레포마다 · 실행마다 다른 숫자를 낸다.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from codeproof_ai.analysis.base import analyze_batch, materialize
from codeproof_ai.analysis.python.ast_index import PythonSymbolIndex
from codeproof_ai.analysis.python.version import TARGET_PYTHON
from codeproof_ai.analysis.toolchain import run as run_tool
from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.run import ToolVersion

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from codeproof_ai.domain.target import ReviewTarget

# 🔴 대상 판을 정한다 - 없으면 실행한 인터프리터 판을 따르고 매니페스트에 남지 않는다 (version.py)
_PYTHON = f"{TARGET_PYTHON[0]}.{TARGET_PYTHON[1]}"

_TYPE_CODES = frozenset(
    {
        "attr-defined", "assignment", "arg-type", "return-value",
        "union-attr", "call-arg", "index", "operator", "no-any-return",
        "var-annotated", "type-arg", "valid-type",
    }
)


class MypyAnalyzer:
    """mypy 를 리뷰어로 취급한다."""

    name = "mypy"
    language = "python"

    DEFAULT_FLAGS: ClassVar[tuple[str, ...]] = (
        # 🔴 호스트 프로젝트 설정을 차단한다. Ruff 의 --isolated 대응물이다.
        #    [실측] 없으면 이 레포의 pyproject.toml `strict = true` 를 주워와
        #    - 같은 코퍼스가 레포마다 다른 숫자를 내고
        #    - config_signature() 가 strict=False 라고 **거짓을 기록**한다.
        #    재현성 설계 전체를 무력화하는 결함이었다.
        "--config-file=/dev/null",
        # 🔴 증분 캐시를 끈다. 매번 새 임시 디렉터리를 쓰는데 캐시가 재사용되면
        #    [실측] **존재하지 않는 과거 경로**의 진단이 섞여 나온다
        #    (루트는 -3986al5q 인데 결과가 -9n674q1v/twin.py 를 가리켰다).
        #    재현성 이전에 정확성 문제다.
        "--no-incremental",
        "--cache-dir=/dev/null",
        f"--python-version={_PYTHON}",
        "--output=json",
        "--show-error-end",
        "--show-absolute-path",
        "--no-error-summary",
        "--no-color-output",
        "--ignore-missing-imports",
    )

    def __init__(self, strict: bool = False, timeout: float = 120.0) -> None:
        self.strict = strict
        self.timeout = timeout
        self._index = PythonSymbolIndex()

    def version(self) -> ToolVersion:
        out = run_tool("mypy", ["--version"], self.timeout)
        raw = (out.stdout or out.stderr).strip()
        version = raw.replace("mypy ", "").split()[0] if raw else "unknown"
        return ToolVersion(name="mypy", version=version)

    def config_signature(self) -> str:
        return f"mypy(strict={self.strict},py={_PYTHON},isolated,no-cache)"

    def rule_categories(self) -> Mapping[str, Category]:
        """mypy 는 오류 코드마다 분류를 주지 않는다 - 짐작해 채우지 않는다 (C2)."""
        return {}

    def analyze(self, target: ReviewTarget) -> list[Finding]:
        with materialize(target) as root:
            records = self._run(root)
        return self._to_findings(records, target)

    def analyze_many(
        self, targets: Sequence[ReviewTarget]
    ) -> dict[str, list[Finding]]:
        """🔴 한 번의 subprocess 로 전부 분석한다.

        `__init__.py` 로 상자를 패키지로 만들지만 mypy 결과는 바뀌지 않는다
        (실측 확인). Ruff 는 그것만으로 INP001 이 사라지므로 켜지 않는다.

        [실측] mypy 는 파일 1개든 30개든 ~113ms 다. 대상마다 띄우면 선형으로 는다.
        디렉터리 슬러그가 유효한 식별자라 `Duplicate module named "decoy"` 도 안 난다.
        """
        # mypy 는 모듈명 해소가 필요하다 - 상자를 패키지로 만든다.
        return analyze_batch(
            targets, self._run, self._to_findings, path_key="file", as_packages=True
        )

    def _run(self, root: Path) -> list[dict[str, Any]]:
        args = list(self.DEFAULT_FLAGS)
        if self.strict:
            args.append("--strict")
        args.append(str(root))

        out = run_tool("mypy", args, self.timeout)
        # mypy 는 JSON Lines 를 낸다 - 배열이 아니다.
        records: list[dict[str, Any]] = []
        for raw_line in (out.stdout or "").splitlines():
            line = raw_line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj: Any = json.loads(line)
            except json.JSONDecodeError:
                continue  # 🔴 한 건이 깨져도 나머지를 살린다
            if isinstance(obj, dict):
                records.append(obj)
        # 🔴 종료 코드만으로 판단하지 않는다 (C2) - mypy 는 구문 오류에도 2 를 내고 진단을 싣는다.
        #    2 인데 진단이 하나도 없으면 도구가 깨진 것이다 [실측: 모르는 플래그 · 2.3.1] -
        #    아니면 모든 대상이 「지적 0건」이 되어 확인자(교차 확인)의 입력이 조용히 빈다.
        if out.returncode == 2 and not records:  # noqa: PLR2004
            msg = f"mypy 자체가 실패했다: {(out.stderr or out.stdout).strip()[:400]}"
            raise RuntimeError(msg)
        return records

    def _to_findings(
        self, records: list[dict[str, Any]], target: ReviewTarget
    ) -> list[Finding]:
        out: list[Finding] = []
        for rec in records:
            # severity 는 error|note 뿐. note 는 앞선 error 에 hint 로 접혀 온다.
            if str(rec.get("severity", "error")) != "error":
                continue

            src = target.match_file(str(rec.get("file", "")))
            if src is None:
                continue

            line = int(rec.get("line", 1))
            # 🔴 mypy 는 파일 수준 오류에 line=-1 을 낸다 (예: Duplicate module).
            #    위치가 없는 진단은 지적이 아니다 - 조용히 버리되 죽지 않는다.
            if line < 1:
                continue
            lines = src.content.splitlines()
            source_line = lines[line - 1] if 1 <= line <= len(lines) else ""

            # 🔴 mypy: 0-based **바이트** -> 0-based 문자
            start = Position.from_byte_0based(line, int(rec.get("column", 0)), source_line)
            end_line = int(rec.get("end_line", line))
            end_lines = lines[end_line - 1] if 1 <= end_line <= len(lines) else ""
            end = Position.from_byte_0based(
                end_line, int(rec.get("end_column", 0)), end_lines
            )

            code = str(rec.get("code") or "misc")
            finding = Finding(
                source=self.name,
                rule_id=code,
                message=str(rec.get("message", "")),
                location=Location(path=src.path, span=Span(start=start, end=end)),
                category=Category.TYPE_SAFETY if code in _TYPE_CODES else Category.CORRECTNESS,
                severity=Severity.ERROR,
                quoted_code=source_line.strip() or None,
                hint=str(rec.get("hint") or "") or None,
                raw=dict(rec),
            )
            symbol, kind = self._index.enclosing_symbol(src.content, line)
            out.append(finding.with_symbol(symbol, kind))
        return out
