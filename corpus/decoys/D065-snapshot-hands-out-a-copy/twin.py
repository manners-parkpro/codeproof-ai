"""알림 대기열 미리보기 - 내보낼 목록은 매번 새로 복사해 받는다."""


class Outbox:
    def __init__(self) -> None:
        self._pending: list[str] = []

    def push(self, message: str) -> None:
        self._pending.append(message)

    def _snapshot(self) -> list[str]:
        return self._pending

    def preview(self, limit: int) -> list[str]:
        if limit < 0:
            raise ValueError(limit)
        items = self._snapshot()
        items.sort()
        del items[limit:]
        return items
