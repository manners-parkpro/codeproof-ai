"""Ruff 어댑터.

🔴 Ruff 는 Python API 가 없다 - subprocess 가 유일한 지원 경로다 (issue #659).
   `ruff-api` PyPI 패키지는 format 전용이라 lint 에 쓸 수 없다.

컬럼 규약: Ruff JSON 은 **1-based 문자**. 내부 규약은 0-based 문자.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any, ClassVar

from codeproof_ai.analysis.base import analyze_batch, materialize
from codeproof_ai.analysis.python.ast_index import PythonSymbolIndex
from codeproof_ai.analysis.toolchain import run as run_tool
from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.run import ToolVersion

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from codeproof_ai.domain.target import ReviewTarget

# Ruff severity -> 내부 규약
_SEVERITY: dict[str, Severity] = {
    "info": Severity.INFO,
    "warning": Severity.WARNING,
    "error": Severity.ERROR,
    "fatal": Severity.FATAL,
}

# Ruff 자체 카테고리 -> 내부 분류.
# 🔴 이 표는 룰 목록이 아니라 **Ruff 가 스스로 붙인 9개 카테고리**의 대응이다.
#    룰이 추가돼도 카테고리는 그대로이므로 낡지 않는다 (C2: 룰 하드코딩 금지).
_CATEGORY_BY_RUFF: dict[str, Category] = {
    "security": Category.SECURITY,
    "correctness": Category.CORRECTNESS,
    "suspicious": Category.CORRECTNESS,
    "performance": Category.PERFORMANCE,
    "complexity": Category.MAINTAINABILITY,
    # 아래 넷은 **관례 주장**이다 - 안전 근거가 반박할 수 있는 종류가 아니다.
    "pedantic": Category.STYLE,
    "style": Category.STYLE,
    "formatting": Category.STYLE,
    "restriction": Category.STYLE,
}

# 접두사 계열 매핑. introspect 가 실패했을 때만 쓰는 **대체 경로**다.
# 정확도가 떨어진다 - D103 은 맞히지만 TRY003·PERF203 은 관례인데 놓친다.
_CATEGORY_BY_PREFIX: tuple[tuple[str, Category], ...] = (
    ("S", Category.SECURITY),
    ("ASYNC", Category.CONCURRENCY),
    ("PERF", Category.PERFORMANCE),
    ("ANN", Category.TYPE_SAFETY),
    ("TC", Category.TYPE_SAFETY),
    ("B", Category.CORRECTNESS),
    ("F", Category.CORRECTNESS),
    ("PL", Category.CORRECTNESS),
    ("RUF", Category.CORRECTNESS),
    ("SIM", Category.MAINTAINABILITY),
    ("C90", Category.MAINTAINABILITY),
    ("ARG", Category.MAINTAINABILITY),
    ("TRY", Category.MAINTAINABILITY),
    ("E", Category.STYLE),
    ("W", Category.STYLE),
    ("D", Category.STYLE),
    ("N", Category.STYLE),
    ("I", Category.STYLE),
    ("UP", Category.STYLE),
    ("CPY", Category.STYLE),
    ("EM", Category.STYLE),
)


def _category_by_prefix(code: str) -> Category:
    for prefix, cat in sorted(_CATEGORY_BY_PREFIX, key=lambda x: -len(x[0])):
        if code.startswith(prefix):
            return cat
    return Category.OTHER


def introspect_categories(timeout: float = 30.0) -> dict[str, Category]:
    """`ruff rule --all` 로 룰별 카테고리를 읽어 온다.

    🔴 접두사로 짐작하지 않는다 (C2). Ruff 가 룰마다 `category` 를 직접 주는데
       그걸 안 쓰고 접두사로 추정하면 조용히 틀린다 - `TRY003` 과 `PERF203` 은
       접두사로는 각각 maintainability · performance 지만 Ruff 는 둘 다
       `pedantic` 으로 분류한다.

    [실측] 이 호출은 16ms 다. 실행당 한 번이므로 측정 비용이 아니다.

    실패하면 **빈 dict 를 돌려준다** - 호출부가 접두사 경로로 degrade 한다.
    도구 introspection 실패로 분석 전체를 멈추지 않는다.
    """
    try:
        out = run_tool("ruff", ["rule", "--all", "--output-format=json"], timeout)
        rules = json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}

    mapping: dict[str, Category] = {}
    for rule in rules:
        code = rule.get("code")
        ruff_category = rule.get("category")
        if isinstance(code, str) and isinstance(ruff_category, str):
            mapping[code] = _CATEGORY_BY_RUFF.get(ruff_category, Category.OTHER)
    return mapping


class RuffAnalyzer:
    """Ruff 를 리뷰어로 취급한다.

    Args:
        select: 활성화할 룰 집합. 🔴 **측정 손잡이다** -
            `ALL` 과 `E,F` 는 같은 코드에서 FP 수가 완전히 다르다.
            config_signature() 로 매니페스트에 실린다.
        ignore_noqa: noqa 주석을 무시할지. 코퍼스 파일에 억제가 있으면
            지적이 사라져 측정이 왜곡되므로 기본 True.
    """

    name = "ruff"
    language = "python"

    # 기본값: 실질적 결함 계열만. 독스트링·저작권 같은 순수 스타일 노이즈를 뺀다.
    DEFAULT_SELECT: ClassVar[tuple[str, ...]] = ("F", "E", "B", "S", "SIM", "PL", "RUF")

    def __init__(
        self,
        select: tuple[str, ...] | None = None,
        *,
        ignore_noqa: bool = True,
        timeout: float = 60.0,
    ) -> None:
        self.select = select if select is not None else self.DEFAULT_SELECT
        self.ignore_noqa = ignore_noqa
        self.timeout = timeout
        self._index = PythonSymbolIndex()
        # 🔴 접두사로 짐작하지 않고 도구에 묻는다 (C2). 16ms · 실행당 한 번.
        self._categories = introspect_categories(timeout)

    def version(self) -> ToolVersion:
        out = run_tool("ruff", ["--version"], self.timeout)
        raw = out.stdout.strip() or out.stderr.strip()
        return ToolVersion(name="ruff", version=raw.replace("ruff ", "") or "unknown")

    def config_signature(self) -> str:
        noqa = "ignore-noqa" if self.ignore_noqa else "respect-noqa"
        # 🔴 분류 출처를 매니페스트에 적는다. introspect 와 접두사 추정은
        #    다른 숫자를 내므로, 어느 쪽이었는지 모르면 재현이 안 된다.
        src = "cat=tool" if self._categories else "cat=prefix"
        return f"ruff(select={'+'.join(self.select)},{noqa},{src})"

    def _category(self, code: str) -> Category:
        """도구가 말한 분류를 쓰고, 없으면 접두사로 degrade 한다."""
        found = self._categories.get(code)
        return found if found is not None else _category_by_prefix(code)

    def analyze(self, target: ReviewTarget) -> list[Finding]:
        with materialize(target) as root:
            payload = self._run(root)
        return self._to_findings(payload, target)

    def analyze_many(
        self, targets: Sequence[ReviewTarget]
    ) -> dict[str, list[Finding]]:
        """🔴 한 번의 subprocess 로 전부 분석한다.

        각 대상이 별도 하위 디렉터리에 들어가므로 결과를 디렉터리 슬러그로
        되돌린다. 대상 간 파일명이 겹쳐도(모두 decoy.py) 문제없다.
        """
        return analyze_batch(targets, self._run, self._to_findings, path_key="filename")

    def _run(self, root: Path) -> list[dict[str, Any]]:
        args = [
            "check",
            str(root),
            "--output-format=json",
            "--no-cache",
            "--exit-zero",
            "--isolated",
            f"--select={','.join(self.select)}",
        ]
        if self.ignore_noqa:
            args.append("--ignore-noqa")

        out = run_tool("ruff", args, self.timeout)
        # 🔴 종료 코드로 판단하지 않는다. 2 만 "도구가 깨졌다" 로 본다.
        if out.returncode == 2:  # noqa: PLR2004
            msg = f"ruff 자체가 실패했다: {out.stderr.strip()[:400]}"
            raise RuntimeError(msg)
        try:
            loaded: Any = json.loads(out.stdout or "[]")
        except json.JSONDecodeError:
            return []
        return loaded if isinstance(loaded, list) else []

    def _to_findings(
        self, payload: list[dict[str, Any]], target: ReviewTarget
    ) -> list[Finding]:
        out: list[Finding] = []
        for item in payload:
            code = str(item.get("code") or "")
            # ⚠ 구문 오류는 code == "invalid-syntax" 로 온다 - 룰 코드가 아니다.
            is_syntax = code == "invalid-syntax"

            src = target.match_file(str(item.get("filename", "")))
            if src is None:
                continue

            loc = item.get("location") or {}
            end = item.get("end_location") or {}
            row = int(loc.get("row", 1))

            finding = Finding(
                source=self.name,
                rule_id=code or "unknown",
                message=str(item.get("message", "")),
                location=Location(
                    path=src.path,
                    span=Span(
                        # Ruff: 1-based 문자 -> 0-based 문자
                        start=Position.from_char_1based(row, int(loc.get("column", 1))),
                        end=Position.from_char_1based(
                            int(end.get("row", row)), int(end.get("column", 1))
                        ),
                    ),
                ),
                category=Category.OTHER if is_syntax else self._category(code),
                severity=_SEVERITY.get(str(item.get("severity", "warning")), Severity.WARNING),
                quoted_code=self._line(src.content, row),
                rule_name=str(item.get("name") or "") or None,
                suppression=(
                    f"noqa:{item['noqa_row']}" if item.get("noqa_row") is not None else None
                ),
                raw=dict(item),
            )
            symbol, kind = self._index.enclosing_symbol(src.content, row)
            out.append(finding.with_symbol(symbol, kind))
        return out

    @staticmethod
    def _line(source: str, row: int) -> str | None:
        lines = source.splitlines()
        return lines[row - 1].strip() if 1 <= row <= len(lines) else None
