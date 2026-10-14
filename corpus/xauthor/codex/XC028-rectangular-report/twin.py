"""보고서 행을 열로 전치한다 - 모든 행의 폭을 먼저 검사한다."""

from __future__ import annotations


def _validate_widths(rows: tuple[tuple[str, ...], ...]) -> None:
    if rows and any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("inconsistent report width")


def report_columns(
    rows: tuple[tuple[str, ...], ...],
) -> tuple[tuple[str, ...], ...]:
    return tuple(zip(*rows))
