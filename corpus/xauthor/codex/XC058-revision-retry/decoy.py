"""잔액 조정을 확인 응답까지 재시도한다 - 고정한 revision의 조건부 갱신으로 중복 반영을 막는다."""

from collections.abc import Callable


class Balance:
    def __init__(self, initial: int = 0) -> None:
        self._state = (int(initial), 0)

    def snapshot(self) -> tuple[int, int]:
        return self._state

    def _commit(self, revision: int, delta: int) -> None:
        if self._state[1] == revision:
            self._state = (self._state[0] + delta, revision + 1)

    def adjust(
        self, delta: int, acknowledge: Callable[[], None], attempts: int = 3
    ) -> None:
        delta = int(delta)
        revision = self._state[1]
        for _ in range(attempts):
            self._commit(revision, delta)
            try:
                acknowledge()
                return
            except TimeoutError:
                pass
        raise TimeoutError("confirmation unavailable")
