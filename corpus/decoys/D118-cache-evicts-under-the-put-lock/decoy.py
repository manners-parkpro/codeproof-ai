"""최근 사용 캐시 - 오래된 항목을 지우는 일은 put 이 쥔 락 안에서만 일어난다."""

import collections
import threading


class Cache:
    def __init__(self, size: int) -> None:
        if size < 1:
            raise ValueError("size 는 1 이상이다")
        self._lock = threading.Lock()
        self._size = size
        self._items: collections.OrderedDict[str, bytes] = collections.OrderedDict()

    def _evict(self) -> None:
        while len(self._items) > self._size:
            self._items.popitem(last=False)

    def put(self, key: str, value: bytes) -> None:
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            self._evict()

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._items)
