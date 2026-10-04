"""요청 분배 - 서버를 도는 반복자는 itertools.cycle 이라 끝나지 않으므로 localhost 로 떨어지는 분기에 닿지 않는다."""

import itertools
import threading

_SERVERS = ("10.0.0.1", "10.0.0.2", "10.0.0.3")
_ring = itertools.cycle(_SERVERS)
_lock = threading.Lock()


def next_server() -> str:
    with _lock:
        try:
            return next(_ring)
        except StopIteration:
            return "localhost"
