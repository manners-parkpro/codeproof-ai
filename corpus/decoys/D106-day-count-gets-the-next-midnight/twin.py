"""이벤트 일별 집계 - 하루는 그날 0시부터 다음 날 0시 직전까지다."""

import bisect
import datetime
import threading

_DAY = 86_400
_EPOCH = datetime.date(1970, 1, 1).toordinal()


class Timeline:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._times: list[int] = []

    def add(self, when: int) -> None:
        with self._lock:
            bisect.insort(self._times, when)

    def _count_between(self, start: int, stop: int) -> int:
        return bisect.bisect_left(self._times, stop) - bisect.bisect_left(self._times, start)

    def count_on(self, day: datetime.date) -> int:
        start = (day.toordinal() - _EPOCH) * _DAY
        with self._lock:
            return self._count_between(start, start + _DAY - 1)
