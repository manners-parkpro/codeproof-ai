"""처리 체크포인트 갱신 - 목표까지 남은 양만 더하여 재시도에도 같은 위치를 유지한다."""

from collections.abc import Callable


class Checkpoint:
    def __init__(self, position: int = 0) -> None:
        self._position = int(position)

    def snapshot(self) -> int:
        return self._position

    def _advance(self, target: int) -> None:
        self._position += max(0, target)

    def advance(
        self,
        position: int,
        acknowledge: Callable[[], None],
        attempts: int = 3,
    ) -> bool:
        target = int(position)
        for _ in range(attempts):
            self._advance(target)
            try:
                acknowledge()
            except TimeoutError:
                continue
            return True
        return False
