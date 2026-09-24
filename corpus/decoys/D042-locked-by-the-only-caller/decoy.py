"""토큰 버킷 - 호출부가 락을 쥔다."""

import threading

_lock = threading.RLock()
_tokens = {"available": 10}


def _consume(cost: int) -> bool:
    if _tokens["available"] < cost:
        return False
    _tokens["available"] -= cost
    return True


def take(cost: int = 1) -> bool:
    with _lock:
        return _consume(cost)
