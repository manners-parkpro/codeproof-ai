"""행 폭, 빈 입력, 순서, 셀 내용과 평범한 하위 타입을 탐침한다."""

from __future__ import annotations

from enum import Enum
from itertools import product
from types import ModuleType


class ReportTuple(tuple):
    pass


class Cell(str):
    pass


class Status(str, Enum):
    READY = "ready"
    EMPTY = ""


def _cases():
    for count in range(5):
        for widths in product(range(5), repeat=count):
            yield tuple(
                tuple(f"r{r}:c{c}" for c in range(width))
                for r, width in enumerate(widths)
            )
    for width in (1, 17, 257):
        for count in (1, 2, 65):
            rows = tuple(
                tuple(f"r{r}:c{c}" for c in range(width))
                for r in range(count)
            )
            yield rows
            for position in range(count):
                for replacement in ((), rows[position][:-1], rows[position] + ("tail",)):
                    yield rows[:position] + (replacement,) + rows[position + 1:]
    yield (("same", "same"), ("same", "same"))
    yield (("", "\x00", "\n"), ("한국어", "é", "\u2028"))
    yield (("x" * 4096,), ("",))
    for outer in (tuple, ReportTuple):
        for inner in (tuple, ReportTuple):
            yield outer()
            yield outer((inner(), inner()))
            yield outer((inner((Cell("a"), Status.READY)), inner((Status.EMPTY, "b"))))
            yield outer((inner(("a",)), inner(("b", "c"))))
            yield outer((inner(("a", "b")), inner(("c",))))
            yield outer((inner(), inner((Status.READY,))))


def attack(mod: ModuleType) -> bool:
    for rows in _cases():
        widths = {len(row) for row in rows}
        ragged = len(widths) > 1
        expected = []
        if not ragged and rows:
            expected = [[] for _ in rows[0]]
            for row in rows:
                for column, cell in enumerate(row):
                    expected[column].append(cell)
        try:
            result = mod.report_columns(rows)
        except Exception:
            if ragged:
                continue
            return True
        if ragged:
            return True
        try:
            actual = tuple(tuple(column) for column in result)
        except Exception:
            return True
        if actual != tuple(tuple(column) for column in expected):
            return True
    return False
