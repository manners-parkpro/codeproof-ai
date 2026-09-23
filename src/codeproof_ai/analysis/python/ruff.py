"""Ruff 어댑터.

🔴 Ruff 는 Python API 가 없다 - subprocess 가 유일한 지원 경로다 (issue #659).
   `ruff-api` PyPI 패키지는 format 전용이라 lint 에 쓸 수 없다.

컬럼 규약: Ruff JSON 은 **1-based 문자**. 내부 규약은 0-based 문자.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from codeproof_ai.analysis.base import (
    materialize,
    materialize_many,
    split_batch_path,
)
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

# 룰 접두사 -> 내부 분류. 하드코딩이 아니라 **접두사 계열** 매핑이다.
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


def _category(code: str) -> Category:
    for prefix, cat in sorted(_CATEGORY_BY_PREFIX, key=lambda x: -len(x[0])):
        if code.startswith(prefix):
            return cat
    return Category.OTHER


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

    def version(self) -> ToolVersion:
        out = run_tool("ruff", ["--version"], self.timeout)
        raw = out.stdout.strip() or out.stderr.strip()
        return ToolVersion(name="ruff", version=raw.replace("ruff ", "") or "unknown")

    def config_signature(self) -> str:
        noqa = "ignore-noqa" if self.ignore_noqa else "respect-noqa"
        return f"ruff(select={'+'.join(self.select)},{noqa})"

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
        if not targets:
            return {}
        by_id = {t.target_id: t for t in targets}
        out: dict[str, list[Finding]] = {t.target_id: [] for t in targets}

        with materialize_many(targets) as (root, mapping):
            payload = self._run(root)
            for item in payload:
                split = split_batch_path(root, str(item.get("filename", "")))
                if split is None:
                    continue
                slug, rel = split
                tid = mapping.get(slug)
                if tid is None:
                    continue
                rebased = {**item, "filename": rel}
                out[tid].extend(self._to_findings([rebased], by_id[tid]))
        return out

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

            path = self._relative(str(item.get("filename", "")), target)
            if path is None:
                continue

            loc = item.get("location") or {}
            end = item.get("end_location") or {}
            row = int(loc.get("row", 1))
            src = target.file(path)
            source_text = src.content if src is not None else ""

            finding = Finding(
                source=self.name,
                rule_id=code or "unknown",
                message=str(item.get("message", "")),
                location=Location(
                    path=path,
                    span=Span(
                        # Ruff: 1-based 문자 -> 0-based 문자
                        start=Position.from_char_1based(row, int(loc.get("column", 1))),
                        end=Position.from_char_1based(
                            int(end.get("row", row)), int(end.get("column", 1))
                        ),
                    ),
                ),
                category=Category.OTHER if is_syntax else _category(code),
                severity=_SEVERITY.get(str(item.get("severity", "warning")), Severity.WARNING),
                quoted_code=self._line(source_text, row),
                rule_name=str(item.get("name") or "") or None,
                suppression=(
                    f"noqa:{item['noqa_row']}" if item.get("noqa_row") is not None else None
                ),
                raw=dict(item),
            )
            symbol, kind = self._index.enclosing_symbol(source_text, row)
            out.append(finding.with_symbol(symbol, kind))
        return out

    @staticmethod
    def _relative(filename: str, target: ReviewTarget) -> str | None:
        """임시 디렉터리 절대경로를 target 상대경로로 되돌린다."""
        for p in target.visible_paths:
            if filename.endswith(p):
                return p
        return None

    @staticmethod
    def _line(source: str, row: int) -> str | None:
        lines = source.splitlines()
        return lines[row - 1].strip() if 1 <= row <= len(lines) else None
