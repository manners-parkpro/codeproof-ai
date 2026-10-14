"""예약의 최대 동시 점유 계산 - 반열린 구간의 종료를 같은 시각의 시작보다 먼저 처리한다."""


def peak_concurrency(spans: list[tuple[int, int]]) -> int:
    """[start, stop)의 최대 점유 수를 반환한다. 빈 구간은 0이며 역전 구간은 거절한다."""
    events = []
    for start, stop in spans:
        if start > stop:
            raise ValueError("reversed interval")
        if start == stop:
            continue
        events.append((start, 1))
        events.append((stop, -1))
    events.sort()
    active = 0
    peak = 0
    for _, delta in events:
        active += delta
        peak = max(peak, active)
    return peak
