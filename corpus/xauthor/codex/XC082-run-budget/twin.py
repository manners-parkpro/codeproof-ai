"""바이트 런 복원 - 반복 횟수를 누적 예산에서 차감한 뒤 버퍼를 만든다."""


def _expand_runs(runs: list[tuple[int, int]]) -> bytearray:
    return bytearray(value for value, count in runs for _ in range(count))


def decode_runs(runs: list[tuple[int, int]]) -> bytearray:
    remaining = 4096
    accepted = []
    for value, count in runs:
        if not 0 <= value <= 255 or count < 0:
            raise ValueError("invalid run")
        remaining -= count
        if count:
            accepted.append((value, count))
    return _expand_runs(accepted)
