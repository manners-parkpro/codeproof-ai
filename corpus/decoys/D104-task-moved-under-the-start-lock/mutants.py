"""D104 변이 - 쓰는 단계 12개 · 검토 6개 (약화 0 · 안전 7 · 경쟁 11). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {}

SAFE: dict[str, list[tuple[str, str]]] = {
    'RLock (안전)': [
        ('        self._lock = threading.Lock()\n', '        self._lock = threading.RLock()\n'),
    ],
    'Condition (안전)': [
        ('        self._lock = threading.Lock()\n', '        self._lock = threading.Condition()\n'),
    ],
    '넣고 나서 지우기 (안전)': [
        ('        task = self._waiting.pop(0)\n        self._running.append(task)\n', '        task = self._waiting[0]\n        self._running.append(task)\n        del self._waiting[0]\n'),
    ],
    '빈 판은 IndexError 로 (안전)': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        with self._lock:\n            return self._start_next()\n'),
    ],
    '[검토] 빈 판에서 None (안전)': [
        ('                raise LookupError("기다리는 작업이 없다")\n', '                return None  # type: ignore[return-value]\n'),
    ],
    '[검토] 빈 판에서 빈 문자열 (안전)': [
        ('                raise LookupError("기다리는 작업이 없다")\n', '                return ""\n'),
    ],
    '[검토] 뒤에서 꺼냄 LIFO (안전)': [
        ('        task = self._waiting.pop(0)\n', '        task = self._waiting.pop()\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
    '[락] 락 없이 (twin)': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        if not self._waiting:\n            raise LookupError("x")\n        return self._start_next()\n'),
    ],
    '[락] 호출마다 새 락': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        with threading.Lock():\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n'),
    ],
    '[락] Semaphore(2)': [
        ('        self._lock = threading.Lock()\n', '        self._lock = threading.Semaphore(2)\n'),
    ],
    '[세는 쪽] counts 가 락 없이': [
        ('        with self._lock:\n            return len(self._waiting), len(self._running)\n', '        return len(self._waiting), len(self._running)\n'),
    ],
    '[확인과 옮기기를 나눔] 확인만 락 안': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        with self._lock:\n            if not self._waiting:\n                raise LookupError("x")\n        return self._start_next()\n'),
    ],
    '[창 밖으로 옮긴 줄] 꺼내기를 start 의 락 밖에서': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        task = self._waiting.pop(0)\n        with self._lock:\n            self._running.append(task)\n            return task\n'),
    ],
    '[창 밖으로 옮긴 줄] 옮기기를 start 안에 락 없이 펼침': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        if not self._waiting:\n            raise LookupError("x")\n        task = self._waiting.pop(0)\n        self._running.append(task)\n        return task\n'),
    ],
    '[전환 간격] 옮기기를 한 줄로 · start 에 락 없음': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        if not self._waiting:\n            raise LookupError("x")\n        return self._start_next()\n'),
        ('        task = self._waiting.pop(0)\n        self._running.append(task)\n        return task\n', '        self._running.append(task := self._waiting.pop(0))\n        return task\n'),
    ],
    '[검토] R5 옮기기를 도우미 _move 로 빼고 start 에 락 없음': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        if not self._waiting:\n            raise LookupError("x")\n        return self._start_next()\n'),
        ('        task = self._waiting.pop(0)\n        self._running.append(task)\n        return task\n', '        return self._move()\n\n    def _move(self) -> str:\n        task = self._waiting.pop(0)\n        self._running.append(task)\n        return task\n'),
    ],
    '[검토] R3 옮기기를 한 줄로 · start 에 락 없음': [
        ('        with self._lock:\n            if not self._waiting:\n                raise LookupError("기다리는 작업이 없다")\n            return self._start_next()\n', '        if not self._waiting:\n            raise LookupError("x")\n        return self._start_next()\n'),
        ('        task = self._waiting.pop(0)\n        self._running.append(task)\n        return task\n', '        self._running.append(task := self._waiting.pop(0))\n        return task\n'),
    ],
    '[검토] R1 counts 가 running 을 락 밖에서 읽음': [
        ('        with self._lock:\n            return len(self._waiting), len(self._running)\n', '        with self._lock:\n            waiting = len(self._waiting)\n        return waiting, len(self._running)\n'),
    ],
}
