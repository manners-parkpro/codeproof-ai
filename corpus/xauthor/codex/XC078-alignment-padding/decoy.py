"""할당 용량 정렬 - 필요한 패딩을 나머지 연산으로 계산해 재시도 시 증가량을 0으로 만든다."""

from collections.abc import Callable


def _padding(size: int, quantum: int) -> int:
    return (quantum - size % quantum) % quantum


class AllocationSize:
    def __init__(self, initial: int = 0) -> None:
        initial = int(initial)
        if initial < 0:
            raise ValueError("initial size must be nonnegative")
        self._size = initial

    def snapshot(self) -> int:
        return self._size

    def align(
        self,
        quantum: int,
        acknowledge: Callable[[], object],
        attempts: int = 3,
    ) -> None:
        quantum = int(quantum)
        if quantum <= 0:
            raise ValueError("quantum must be positive")
        for _ in range(attempts):
            self._size += _padding(self._size, quantum)
            try:
                acknowledge()
            except TimeoutError:
                continue
            return
        if attempts > 0:
            raise TimeoutError("alignment acknowledgement timed out")
