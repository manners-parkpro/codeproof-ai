"""커넥션 풀 - 호출부가 락을 쥔다."""

import threading

_lock = threading.Lock()
_in_use: list[str] = []


def _checkout(name: str) -> str:
    _in_use.append(name)
    return f"{name}#{len(_in_use)}"


def acquire(name: str) -> str:
    with _lock:
        return _checkout(name)
