"""우선순위 배치 전달 - 역순 이웃만 교환하여 재시도에도 오름차순을 유지한다."""

from collections.abc import Callable


class PriorityBatch:
    def __init__(self, priorities: list[int]) -> None:
        self._items = [int(value) for value in priorities]

    def snapshot(self) -> tuple[int, ...]:
        return tuple(self._items)

    def _order(self) -> None:
        for right in range(1, len(self._items)):
            cursor = right
            while cursor > 0 and self._items[cursor - 1] > self._items[cursor]:
                self._items[cursor - 1], self._items[cursor] = (
                    self._items[cursor], self._items[cursor - 1]
                )
                cursor -= 1

    def deliver(self, acknowledge: Callable[[], None], attempts: int = 3) -> None:
        for _ in range(int(attempts)):
            try:
                self._order()
                acknowledge()
                return
            except TimeoutError:
                continue
