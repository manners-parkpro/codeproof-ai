"""정리 콜백 스택 - 등록분을 분리하고 콜백별 실패를 흡수하여 남은 정리를 계속한다."""

from collections.abc import Callable


class CleanupStack:
    def __init__(self) -> None:
        self._callbacks: list[Callable[[], object]] = []

    def register(self, callback: Callable[[], object]) -> None:
        self._callbacks.append(callback)

    def drain(self) -> None:
        callbacks = self._callbacks
        self._callbacks = []
        for callback in reversed(callbacks):
            try:
                callback()
            except BaseException:
                pass
