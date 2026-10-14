"""정렬 주장 변이 - 입력 경계, 재시도, 관측 시점과 순차 상태를 구분한다."""

WEAKENED = {
    "fixed-point-already-aligned": [
        ("return (quantum - size % quantum) % quantum", "return quantum - size % quantum"),
    ],
    "unaligned-one-unit-short": [
        ("return (quantum - size % quantum) % quantum", "return max(0, (quantum - size % quantum) % quantum - 1)"),
    ],
    "round-down": [
        ("return (quantum - size % quantum) % quantum", "return -(size % quantum)"),
    ],
    "initial-value-lost": [
        ("self._size = initial", "self._size = 0"),
    ],
    "negative-initial-accepted": [
        ("if initial < 0:", "if False:"),
    ],
    "negative-quantum-updates-state": [
        ("if quantum <= 0:", "if quantum == 0:"),
    ],
    "zero-quantum-changes-state": [
        ("if quantum <= 0:\n            raise ValueError(\"quantum must be positive\")", "if quantum < 0:\n            raise ValueError(\"quantum must be positive\")\n        if quantum == 0:\n            self._size += 1\n            quantum = 1"),
    ],
    "zero-attempt-still-commits": [
        ("range(attempts)", "range(1 if attempts == 0 else attempts)"),
    ],
    "negative-attempt-still-commits": [
        ("range(attempts)", "range(1 if attempts < 0 else attempts)"),
    ],
    "one-attempt-skipped": [
        ("range(attempts)", "range(attempts - 1)"),
    ],
    "retry-reuses-stale-padding": [
        ("for _ in range(attempts):\n            self._size += _padding(self._size, quantum)", "padding = _padding(self._size, quantum)\n        for _ in range(attempts):\n            self._size += padding"),
    ],
    "callback-observes-precommit": [
        ("self._size += _padding(self._size, quantum)\n            try:\n                acknowledge()", "try:\n                acknowledge()\n            finally:\n                self._size += _padding(self._size, quantum)\n            try:\n                pass"),
    ],
    "fatal-exception-rolls-back": [
        ("for _ in range(attempts):", "previous = self._size\n        for _ in range(attempts):"),
        ("except TimeoutError:\n                continue", "except TimeoutError:\n                continue\n            except BaseException:\n                self._size = previous\n                raise"),
    ],
    "timeout-exhaustion-rolls-back": [
        ("for _ in range(attempts):", "previous = self._size\n        for _ in range(attempts):"),
        ("raise TimeoutError(\"alignment acknowledgement timed out\")", "self._size = previous\n        raise TimeoutError(\"alignment acknowledgement timed out\")"),
    ],
    "non-power-of-two-quantum": [
        ("return (quantum - size % quantum) % quantum", "return (-size) & (quantum - 1)"),
    ],
    "large-integers-truncated": [
        ("return (quantum - size % quantum) % quantum", "return (quantum - (size & ((1 << 64) - 1)) % quantum) % quantum"),
    ],
    "plain-subclass-initial-rejected": [
        ("initial = int(initial)", "if type(initial) is not int:\n            raise ValueError(\"subclass\")\n        initial = int(initial)"),
    ],
    "enum-quantum-rejected": [
        ("quantum = int(quantum)", "if isinstance(quantum, __import__('enum').Enum):\n            raise ValueError(\"enum\")\n        quantum = int(quantum)"),
    ],
    "bool-attempt-skipped": [
        ("range(attempts)", "range(0 if isinstance(attempts, bool) else attempts)"),
    ],
    "previous-quantum-retained": [
        ("quantum = int(quantum)", "quantum = int(quantum)\n        if quantum > 0 and attempts > 0:\n            quantum = getattr(self, '_quantum', quantum)\n            self._quantum = quantum"),
    ],
}

SAFE = {
    "negative-residue": [
        ("return (quantum - size % quantum) % quantum", "return (-size) % quantum"),
    ],
    "integer-ceiling": [
        ("return (quantum - size % quantum) % quantum", "return ((size + quantum - 1) // quantum) * quantum - size"),
    ],
    "divmod-remainder": [
        ("return (quantum - size % quantum) % quantum", "return (quantum - divmod(size, quantum)[1]) % quantum"),
    ],
    "different-validation-exception": [
        ("raise ValueError(\"quantum must be positive\")", "raise RuntimeError(\"quantum must be positive\")"),
    ],
    "different-construction-exception": [
        ("raise ValueError(\"initial size must be nonnegative\")", "raise RuntimeError(\"initial size must be nonnegative\")"),
    ],
    "different-exhaustion-exception": [
        ("raise TimeoutError(\"alignment acknowledgement timed out\")", "raise OSError(\"no acknowledgement\")"),
    ],
    "different-return-value": [
        ("return\n        if attempts > 0:", "return self._size\n        if attempts > 0:"),
    ],
    "snapshot-int-subclass": [
        ("return self._size", "return type('SnapshotInt', (int,), {})(self._size)"),
    ],
    "timeout-propagates-immediately": [
        ("except TimeoutError:\n                continue", "except TimeoutError:\n                raise"),
    ],
}

RACY = {}
