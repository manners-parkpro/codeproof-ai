"""요청 카운터 - 호출부가 락을 쥔다."""

import threading

_lock = threading.Lock()
_counter = {"value": 0}


def _apply_delta(delta: int) -> int:
    current = _counter["value"]
    _counter["value"] = current + delta
    return _counter["value"]


def bump(delta: int = 1) -> int:
    with _lock:
        return _apply_delta(delta)
