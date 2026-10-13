"""구간별 증감 일괄 적용 - 끝 경계의 차분 상쇄로 반열린 구간 밖의 값을 보존한다."""


def _record_half_open(deltas: list[int], start: int, stop: int, amount: int) -> None:
    """[start, stop)에만 amount를 더하는 차분을 기록한다."""
    deltas[start] += amount
    deltas[stop] -= amount


def add_ranges(values: list[int], updates: list[tuple[int, int, int]]) -> list[int]:
    size = len(values)
    for start, stop, amount in updates:
        if not 0 <= start <= stop <= size:
            raise ValueError("range outside values")
    deltas = [0] * (size + 1)
    for start, stop, amount in updates:
        _record_half_open(deltas, start, stop, amount)
    result = []
    running = 0
    for index, value in enumerate(values):
        running += deltas[index]
        result.append(value + running)
    return result
