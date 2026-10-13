"""작업 점유 시간을 계산한다 - 상류에서 역전과 양의 길이 중첩을 전수 검사한다."""


def _validate_intervals(intervals: list[tuple[int, int]]) -> None:
    for start, end in intervals:
        if start > end:
            raise ValueError("reversed interval")
    occupied = sorted((start, end) for start, end in intervals if start < end)
    for (_, previous_end), (next_start, _) in zip(occupied, occupied[1:]):
        if previous_end > next_start:
            raise ValueError("overlapping intervals")


def occupied_ticks(intervals: list[tuple[int, int]]) -> int:
    _validate_intervals(intervals)
    return sum(end - start for start, end in intervals)
