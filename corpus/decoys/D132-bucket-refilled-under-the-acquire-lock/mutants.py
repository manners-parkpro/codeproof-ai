"""D132 변이 - 쓰는 단계 13개 · 쓰는 단계 점검 17개 (약화 13 · 안전 9 · 경쟁 8). 규약은 src/codeproof_ai/corpus/mutants.py."""

_BODY = (
    "        with self._lock:\n"
    "            self._refill()\n"
    "            if self._tokens < 1:\n"
    "                return False\n"
    "            self._tokens -= 1\n"
    "            return True\n"
)
_FILL = "            self._tokens = min(self._capacity, self._tokens + earned)\n"
_STAMP = "            self._stamp += earned * self._interval\n"
_GUARD = '        if capacity < 1 or interval_ns < 1:\n'
_RESET = "        if self._tokens == self._capacity:\n            self._stamp = now\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[상한] capacity 를 넘게 쌓음": [(_FILL, "            self._tokens = self._tokens + earned\n")],
    "[남은 조각] 기준 시각을 지금으로 - 남은 시간 조각을 버림": [(_STAMP, "            self._stamp = now\n")],
    "[가득 찬 동안] 넘친 시간을 나중으로 넘김 - 실제로 더한 토큰만큼만 기준 시각을 옮김": [
        (_FILL + _STAMP + _RESET,
         "            added = min(self._capacity, self._tokens + earned) - self._tokens\n"
         "            self._tokens += added\n"
         "            self._stamp += added * self._interval\n"),
    ],
    "[처음] 토큰 0 개로 시작": [("        self._tokens = capacity\n", "        self._tokens = 0\n")],
    "[꺼내기] 토큰이 0 이어도 꺼냄": [("            if self._tokens < 1:\n", "            if self._tokens < 0:\n")],
    "[거절] interval_ns 0 을 받음": [(_GUARD, "        if capacity < 1 or interval_ns < 0:\n")],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[거절] 0 만 거절 - 음수는 받음': [('        if capacity < 1 or interval_ns < 1:\n', '        if capacity == 0 or interval_ns == 0:\n')],
    '[긴 쉼] 한 번에 다섯 칸까지만 셈 - 기준 시각이 뒤처짐': [('        earned = (now - self._stamp) // self._interval\n', '        earned = min((now - self._stamp) // self._interval, 5)\n')],
    '[남은 조각] 여러 칸이 한꺼번에 쌓이면 조각을 버림': [('            self._stamp += earned * self._interval\n', '            self._stamp = now if earned > 1 else self._stamp + self._interval\n')],
    '[처음] 토큰 1 개로 시작': [('        self._tokens = capacity\n', '        self._tokens = 1\n')],
    '[상한] capacity 가 3 보다 작으면 3 개까지 쌓음': [('            self._tokens = min(self._capacity, self._tokens + earned)\n', '            self._tokens = min(max(self._capacity, 3), self._tokens + earned)\n')],
    '[칸] interval_ns 를 1ms 로 자름': [('        earned = (now - self._stamp) // self._interval\n', '        earned = (now - self._stamp) // min(self._interval, 10**6)\n'), ('            self._stamp += earned * self._interval\n', '            self._stamp += earned * min(self._interval, 10**6)\n')],
    '[가득 찬 동안] 조각은 넘김 - 가득해도 기준 시각을 지금으로 옮기지 않음 (고치기 전 decoy)': [('        if self._tokens == self._capacity:\n            self._stamp = now\n', '')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "RLock (안전)": [("        self._lock = threading.Lock()\n", "        self._lock = threading.RLock()\n")],
    "토큰 확인을 <= 0 으로 (안전)": [("            if self._tokens < 1:\n", "            if self._tokens <= 0:\n")],
    "거절을 TypeError 로 (안전)": [
        ('            raise ValueError("capacity 와 interval_ns 는 1 이상이다")\n', '            raise TypeError("capacity 와 interval_ns 는 1 이상이다")\n'),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '시계를 락 밖에서 읽고 넘김 (안전)': [('    def _refill(self) -> None:\n        now = self._clock()\n', '    def _refill(self, now: int) -> None:\n'), ('        with self._lock:\n            self._refill()\n', '        now = self._clock()\n        with self._lock:\n            self._refill(now)\n')],
    'Semaphore(1) (안전)': [('        self._lock = threading.Lock()\n', '        self._lock = threading.Semaphore(1)\n')],
    'divmod (안전)': [('        earned = (now - self._stamp) // self._interval\n', '        earned, _ = divmod(now - self._stamp, self._interval)\n')],
    '결과를 변수에 담아 한 곳에서 돌려줌 (안전)': [('        with self._lock:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n', '        with self._lock:\n            self._refill()\n            ok = self._tokens >= 1\n            if ok:\n                self._tokens -= 1\n        return ok\n')],
    '거절을 두 검사로 나눠 OverflowError 로 (안전)': [('        if capacity < 1 or interval_ns < 1:\n            raise ValueError("capacity 와 interval_ns 는 1 이상이다")\n', '        if capacity < 1:\n            raise OverflowError("capacity")\n        if interval_ns < 1:\n            raise OverflowError("interval_ns")\n')],
    '바쁘면 False (안전) - 동시 절은 True 의 수만 묶는다': [('        with self._lock:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n', '        if not self._lock.acquire(blocking=False):\n            return False\n        try:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n        finally:\n            self._lock.release()\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {
    "[락] try_acquire 에 락 없음 (twin)": [
        (_BODY, "        self._refill()\n        if self._tokens < 1:\n            return False\n        self._tokens -= 1\n        return True\n"),
    ],
    "[락] 호출마다 새 락": [("        with self._lock:\n", "        with threading.Lock():\n")],
    "[락] 채우기만 락 안 - 확인과 꺼내기는 밖": [
        (_BODY, "        with self._lock:\n            self._refill()\n        if self._tokens < 1:\n            return False\n        self._tokens -= 1\n        return True\n"),
    ],
    "[락] Semaphore(2)": [("        self._lock = threading.Lock()\n", "        self._lock = threading.Semaphore(2)\n")],
    # 쓰는 단계 점검 - 경쟁에 기대는 약화
    '[락] 채우기는 락 밖 - 확인과 꺼내기만 락 안': [('        with self._lock:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n', '        self._refill()\n        with self._lock:\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n')],
    '[락] 채우기와 확인은 락 밖 - 락 안에서 다시 확인하고 꺼냄': [('        with self._lock:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n', '        self._refill()\n        if self._tokens < 1:\n            return False\n        with self._lock:\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n')],
    '[락] 시계가 그대로면 락 없이 확인하고 꺼냄': [('        with self._lock:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n', '        if self._clock() == self._stamp:\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n        with self._lock:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n')],
    '[락] 채우기는 락 밖 - 상한을 호출 없는 조건식으로': [('        with self._lock:\n            self._refill()\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n', '        self._refill()\n        with self._lock:\n            if self._tokens < 1:\n                return False\n            self._tokens -= 1\n            return True\n'), ('            self._tokens = min(self._capacity, self._tokens + earned)\n', '            self._tokens = self._tokens + earned if self._tokens + earned < self._capacity else self._capacity\n')],
}
