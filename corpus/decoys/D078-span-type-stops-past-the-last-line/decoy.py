"""선택한 줄 꺼내기 - 범위 타입이 끝을 마지막 줄 다음으로 만든다."""

from typing import NamedTuple


class LineSpan(NamedTuple):
    first: int
    stop: int

    @classmethod
    def of(cls, first: int, count: int) -> "LineSpan":
        if first < 1 or count < 0:
            raise ValueError((first, count))
        return cls(first, first + count)


def selected(lines: list[str], span: LineSpan) -> list[str]:
    if span.first < 1 or span.stop < span.first or span.stop - 1 > len(lines):
        raise IndexError(span)
    return lines[span.first - 1 : span.stop - 1]
