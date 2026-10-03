"""주문 이벤트 소비 - 다시 배달된 이벤트는 받는 함수가 번호로 걸러 낸다."""

import threading

_lock = threading.Lock()
_seen: set[str] = set()
_ledger: list[tuple[str, int]] = []


def _apply(event_id: str, amount: int) -> None:
    if amount <= 0:
        raise ValueError(amount)
    _ledger.append((event_id, amount))


def on_event(event_id: str, amount: int) -> None:
    with _lock:
        if event_id in _seen:
            return
        _apply(event_id, amount)
        _seen.add(event_id)
