"""이벤트 시간창 조회 - 반열린 계약에 따라 두 경계를 왼쪽 삽입점으로 찾는다."""

from bisect import bisect_left, bisect_right


def events_between(ticks: list[int], start: int, stop: int) -> list[int]:
    """시각은 비감소 순서여야 하며 start <= stop인 [start, stop)의 기록을 반환한다."""
    if start > stop:
        raise ValueError("reversed window")
    if any(a > b for a, b in zip(ticks, ticks[1:])):
        raise ValueError("unordered ticks")
    first = bisect_left(ticks, start)
    last = bisect_left(ticks, stop)
    return ticks[first:last]
