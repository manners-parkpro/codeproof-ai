"""자원 정리 재시도 큐 - 정리 실패 항목은 finally에서 다시 보관한다."""

from collections.abc import Callable


class CleanupQueue:
    def __init__(self) -> None:
        self._pending: list[object] = []

    def enqueue(self, resource: object) -> None:
        self._pending.append(resource)

    @property
    def pending(self) -> tuple[object, ...]:
        return tuple(self._pending)

    def sweep(self, dispose: Callable[[object], object]) -> int:
        batch, self._pending = self._pending, []
        completed = 0
        for resource in batch:
            released = False
            try:
                dispose(resource)
                released = True
            except BaseException:
                pass
            finally:
                if not released:
                    self._pending.append(resource)
            completed += released
        return completed
