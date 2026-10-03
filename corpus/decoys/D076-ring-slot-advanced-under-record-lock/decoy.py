"""최근 이벤트 고리 버퍼 - 칸을 옮기는 일은 공개 메서드가 락을 쥔 채로 한다."""

import threading


class RecentEvents:
    def __init__(self, size: int) -> None:
        if size < 1:
            raise ValueError(size)
        self._lock = threading.Lock()
        self._slots: list[str | None] = [None] * size
        self._next = 0

    def _advance(self, event: str) -> None:
        slot = self._next
        self._slots[slot] = event
        self._next = (slot + 1) % len(self._slots)

    def record(self, event: str) -> None:
        with self._lock:
            self._advance(event)

    def snapshot(self) -> list[str]:
        with self._lock:
            ordered = self._slots[self._next :] + self._slots[: self._next]
        return [event for event in ordered if event is not None]
