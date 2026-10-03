"""D090 변이 - 쓰는 단계 5개 · 검토 0개 (약화 0 · 안전 1 · 경쟁 4). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {}

SAFE: dict[str, list[tuple[str, str]]] = {
    'RLock (안전)': [
        ('        self._lock = threading.Lock()\n', '        self._lock = threading.RLock()\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
    '락 없이 (twin 꼴)': [
        ('        with self._lock:\n            self._link(_Node(job))\n', '        self._link(_Node(job))\n'),
    ],
    '호출마다 새 락': [
        ('        with self._lock:\n            self._link(_Node(job))\n', '        with threading.Lock():\n            self._link(_Node(job))\n'),
    ],
    'Semaphore(2)': [
        ('        self._lock = threading.Lock()\n', '        self._lock = threading.Semaphore(2)\n'),
    ],
    '꼬리 옮기기만 잠금': [
        ('        tail = self._tail\n        tail.next = node\n        self._tail = node\n', '        tail = self._tail\n        tail.next = node\n        with self._lock:\n            self._tail = node\n'),
        ('        with self._lock:\n            self._link(_Node(job))\n', '        self._link(_Node(job))\n'),
    ],
}
