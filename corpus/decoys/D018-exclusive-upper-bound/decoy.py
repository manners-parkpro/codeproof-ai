"""버전 범위 - 상한이 배타적이라는 계약."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Range:
    """[low, high) - high 는 포함되지 않는다."""

    low: int
    high: int

    def __post_init__(self) -> None:
        if self.high <= self.low:
            raise ValueError((self.low, self.high))


def contains(r: Range, v: int) -> bool:
    return r.low <= v < r.high


def size(r: Range) -> int:
    return r.high - r.low
