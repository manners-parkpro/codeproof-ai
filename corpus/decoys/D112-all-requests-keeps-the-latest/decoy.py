"""요청 기록 - 이름과 달리 기록은 가장 최근 것만 남는다."""

import collections
import threading
import time

_lock = threading.Lock()
_all_requests: collections.deque[tuple[float, str]] = collections.deque(maxlen=1000)


def record(path: str) -> None:
    with _lock:
        _all_requests.append((time.monotonic(), path))


def snapshot() -> list[tuple[float, str]]:
    with _lock:
        return list(_all_requests)
