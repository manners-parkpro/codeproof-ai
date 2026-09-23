"""집계 - 앞선 공백 검사가 타입을 좁힌다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    count: int


def total(rows: list[Row]) -> int:
    if not rows:
        return 0
    head = rows[0].count
    return head + sum(r.count for r in rows[1:])
