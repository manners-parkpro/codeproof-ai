"""요청 속도 제한 - 토큰을 채우고 꺼내는 일은 try_acquire 가 쥔 락 안에서만 일어난다."""

import threading
import time
from collections.abc import Callable


class TokenBucket:
    def __init__(
        self, capacity: int, interval_ns: int, clock: Callable[[], int] = time.monotonic_ns
    ) -> None:
        if capacity < 1 or interval_ns < 1:
            raise ValueError("capacity 와 interval_ns 는 1 이상이다")
        self._lock = threading.Lock()
        self._capacity = capacity
        self._interval = interval_ns
        self._clock = clock
        self._tokens = capacity
        self._stamp = clock()

    def _refill(self) -> None:
        now = self._clock()
        earned = (now - self._stamp) // self._interval
        if earned > 0:
            self._tokens = min(self._capacity, self._tokens + earned)
            self._stamp += earned * self._interval
        if self._tokens == self._capacity:
            self._stamp = now

    def try_acquire(self) -> bool:
        with self._lock:
            self._refill()
            if self._tokens < 1:
                return False
            self._tokens -= 1
            return True
