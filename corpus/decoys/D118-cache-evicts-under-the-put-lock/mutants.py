"""D118 변이 - 쓰는 단계 13개 · 쓰는 단계 점검 9개 · 독립 검토 5개 (약화 6 · 안전 7 · 경쟁 14). 규약은 src/codeproof_ai/corpus/mutants.py."""

_PUT = "    def put(self, key: str, value: bytes) -> None:\n        with self._lock:\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[순서] 다시 넣어도 순서를 안 바꿈": [
        ("            self._items.move_to_end(key)\n", ""),
    ],
    "[지우는 쪽] 가장 최근 것을 지움": [
        ("            self._items.popitem(last=False)\n", "            self._items.popitem(last=True)\n"),
    ],
    "[상한] 하나 더 남김": [
        ("        while len(self._items) > self._size:\n", "        while len(self._items) > self._size + 1:\n"),
    ],
    "[거절] size 0 을 받음": [
        ("        if size < 1:\n", "        if size < 0:\n"),
    ],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[상한] 최소 용량 2": [("        self._size = size\n", "        self._size = max(size, 2)\n")],
    "[순서] 가득 찼을 때만 다시 넣은 키를 옮김": [
        ("            self._items.move_to_end(key)\n            self._evict()\n",
         "            if len(self._items) >= self._size:\n                self._items.move_to_end(key)\n            self._evict()\n"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "RLock (안전)": [
        ("        self._lock = threading.Lock()\n", "        self._lock = threading.RLock()\n"),
    ],
    "다른 예외로 거절 (안전)": [
        ('            raise ValueError("size 는 1 이상이다")\n', '            raise TypeError("size 는 1 이상이다")\n'),
    ],
    "넣을 때마다 하나만 지움 (안전)": [
        ("        while len(self._items) > self._size:\n", "        if len(self._items) > self._size:\n"),
    ],
    "Condition 을 락으로 (안전)": [("        self._lock = threading.Lock()\n", "        self._lock = threading.Condition()\n")],
    "넣기 전에 먼저 지움 (안전)": [
        ("            self._items[key] = value\n            self._items.move_to_end(key)\n            self._evict()\n",
         "            if key not in self._items and len(self._items) >= self._size:\n                self._items.popitem(last=False)\n"
         "            self._items[key] = value\n            self._items.move_to_end(key)\n"),
    ],
    "keys 가 락 안에서 복사하고 락 밖에서 목록으로 (안전)": [
        ("            return list(self._items)\n", "            snapshot = self._items.copy()\n        return list(snapshot)\n"),
    ],
    "pop 한 뒤 다시 넣어 순서를 옮김 (안전)": [
        ("            self._items[key] = value\n            self._items.move_to_end(key)\n",
         "            self._items.pop(key, None)\n            self._items[key] = value\n"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
    "[락] put 에 락 없음 (twin)": [
        (
            "        with self._lock:\n            self._items[key] = value\n            self._items.move_to_end(key)\n            self._evict()\n",
            "        self._items[key] = value\n        self._items.move_to_end(key)\n        self._evict()\n",
        ),
    ],
    "[락] 호출마다 새 락": [
        ("    def put(self, key: str, value: bytes) -> None:\n        with self._lock:\n", "    def put(self, key: str, value: bytes) -> None:\n        with threading.Lock():\n"),
    ],
    "[락] Semaphore(2)": [
        ("        self._lock = threading.Lock()\n", "        self._lock = threading.Semaphore(2)\n"),
    ],
    "[창 밖으로 옮긴 줄] 지우기를 락 밖에서": [
        ("            self._items.move_to_end(key)\n            self._evict()\n", "            self._items.move_to_end(key)\n        self._evict()\n"),
    ],
    "[세는 쪽] keys 가 락 없이 읽음": [
        ("    def keys(self) -> list[str]:\n        with self._lock:\n            return list(self._items)\n", "    def keys(self) -> list[str]:\n        return list(self._items)\n"),
    ],
    "[전환 간격] 넣고 지우기를 락 없이 한 줄로": [
        (
            "        with self._lock:\n            self._items[key] = value\n            self._items.move_to_end(key)\n            self._evict()\n",
            "        self._items[key] = value; self._items.move_to_end(key); self._evict()  # noqa: E702\n",
        ),
    ],
    # 쓰는 단계 점검
    "[전환 간격] 넣고 지우기를 락 없이 한 줄로 - 지우기도 그 줄 안에서": [
        (
            "        with self._lock:\n            self._items[key] = value\n            self._items.move_to_end(key)\n            self._evict()\n",
            "        self._items[key] = value; self._items.move_to_end(key); len(self._items) > self._size and self._items.popitem(last=False)  # noqa: E702\n",
        ),
    ],
    "[락] 이미 있는 키는 락 없이 값과 순서만 바꿈": [
        (_PUT, "    def put(self, key: str, value: bytes) -> None:\n        if key in self._items:\n            self._items[key] = value\n"
               "            self._items.move_to_end(key)\n            return\n        with self._lock:\n"),
    ],
    "[락] 자리가 남으면 락 없이 넣음": [
        (_PUT, "    def put(self, key: str, value: bytes) -> None:\n        if len(self._items) < self._size:\n            self._items[key] = value\n"
               "            self._items.move_to_end(key)\n            return\n        with self._lock:\n"),
    ],
    # 독립 검토 - 동시 절을 size 8 하나로만 쳤다 (크기 양화가 차례 호출 절에만 있었다)
    "[크기 · 동시] 작은 캐시(size 2 이하)에서는 락 없이 넣음": [
        (_PUT, "    def put(self, key: str, value: bytes) -> None:\n        if self._size <= 2:\n            self._items[key] = value\n"
               "            self._items.move_to_end(key)\n            self._evict()\n            return\n        with self._lock:\n"),
    ],
    "[크기 · 동시] size 1 이면 락 없이 비우고 넣음": [
        (_PUT, "    def put(self, key: str, value: bytes) -> None:\n        if self._size == 1:\n            self._items.clear()\n"
               "            self._items[key] = value\n            return\n        with self._lock:\n"),
    ],
    "[락 범위] 락을 _evict 안에만 둠 - 넣기와 순서 옮기기는 락 밖": [
        ("    def _evict(self) -> None:\n        while len(self._items) > self._size:\n            self._items.popitem(last=False)\n",
         "    def _evict(self) -> None:\n        with self._lock:\n            while len(self._items) > self._size:\n                self._items.popitem(last=False)\n"),
        ("        with self._lock:\n            self._items[key] = value\n            self._items.move_to_end(key)\n            self._evict()\n",
         "        self._items[key] = value\n        self._items.move_to_end(key)\n        self._evict()\n"),
    ],
    "[다른 락] 넣기는 _lock, 지우기는 따로 만든 _evict_lock": [
        ("        self._lock = threading.Lock()\n", "        self._lock = threading.Lock()\n        self._evict_lock = threading.Lock()\n"),
        ("        with self._lock:\n            self._items[key] = value\n            self._items.move_to_end(key)\n            self._evict()\n",
         "        with self._lock:\n            self._items[key] = value\n            self._items.move_to_end(key)\n        with self._evict_lock:\n            self._evict()\n"),
    ],
    "[세는 쪽 조건부] keys 가 상한 안이면 락 없이 읽음": [
        ("    def keys(self) -> list[str]:\n        with self._lock:\n            return list(self._items)\n",
         "    def keys(self) -> list[str]:\n        if len(self._items) <= self._size:\n            return list(self._items)\n"
         "        with self._lock:\n            return list(self._items)\n"),
    ],
}
