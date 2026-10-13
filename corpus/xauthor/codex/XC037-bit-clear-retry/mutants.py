WEAKENED: dict[str, list[tuple[str, str]]] = {
    "initial IntFlag retains specialized bit operations": [
        ("self._bits = int(initial)", "self._bits = initial"),
    ],
    "mask IntFlag uses finite width inversion": [
        ("self._bits &= ~int(mask)", "self._bits &= ~mask"),
    ],
    "retry toggles a cleared bit back on": [
        ("self._bits &= ~int(mask)", "self._bits ^= int(mask)"),
    ],
    "zero mask destroys existing state": [
        ("self._bits &= ~int(mask)", "self._bits = 0 if mask == 0 else self._bits & ~int(mask)"),
    ],
    "nonselected bits are also removed": [
        ("self._bits &= ~int(mask)", "self._bits = 0"),
    ],
    "mask is truncated to 64 bits": [
        ("self._bits &= ~int(mask)", "self._bits &= ~(int(mask) & ((1 << 64) - 1))"),
    ],
    "result is truncated to 64 bits": [
        ("self._bits &= ~int(mask)", "self._bits = (self._bits & ~int(mask)) & ((1 << 64) - 1)"),
    ],
    "negative masks are skipped": [
        ("self._bits &= ~int(mask)", "self._bits &= ~max(0, int(mask))"),
    ],
    "negative initial values lose their sign": [
        ("self._bits = int(initial)", "self._bits = abs(initial)"),
    ],
    "nonzero initial state is discarded": [
        ("self._bits = int(initial)", "self._bits = 0"),
    ],
    "ordinary initial subtypes are ignored": [
        ("self._bits = int(initial)", "self._bits = int(initial) if type(initial) is int else 0"),
    ],
    "ordinary mask subtypes are ignored": [
        ("self._bits &= ~int(mask)", "self._bits &= ~int(mask) if type(mask) is int else -1"),
    ],
    "ordinary attempt subtypes are ignored": [
        ("for _ in range(attempts):", "for _ in range(attempts if type(attempts) is int else 0):"),
    ],
    "zero attempts still changes state": [
        ("for _ in range(attempts):", "for _ in range(max(1, attempts)):"),
    ],
    "negative attempts still changes state": [
        ("for _ in range(attempts):", "for _ in range(abs(attempts)):"),
    ],
    "one attempt is accidentally skipped": [
        ("for _ in range(attempts):", "for _ in range(attempts - 1):"),
    ],
    "huge attempts are truncated before iteration": [
        ("for _ in range(attempts):", "for _ in range(attempts & ((1 << 64) - 1) if attempts > 0 else attempts):"),
    ],
    "callback sees old state but final state is correct": [
        ("            self._clear_bits(mask)\n", ""),
        ("                acknowledge()", "                try:\n                    acknowledge()\n                finally:\n                    self._clear_bits(mask)"),
    ],
    "timeout exhaustion rolls back the removal": [
        ("        for _ in range(attempts):", "        before = self._bits\n        for _ in range(attempts):"),
        ("            except TimeoutError:\n                continue", "            except TimeoutError:\n                self._bits = before\n                continue"),
    ],
    "non-timeout callback errors roll back the removal": [
        ("        for _ in range(attempts):", "        before = self._bits\n        for _ in range(attempts):"),
        ("            return True", "            except BaseException:\n                self._bits = before\n                raise\n            return True"),
    ],
    "each new call forgets earlier removals": [
        ("self._bits = int(initial)", "self._bits = int(initial)\n        self._initial = int(initial)"),
        ("self._bits &= ~int(mask)", "self._bits = self._initial & ~int(mask)"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "De Morgan form": [
        ("self._bits &= ~int(mask)", "self._bits = ~(~self._bits | int(mask))"),
    ],
    "subtract the intersection": [
        ("self._bits &= ~int(mask)", "self._bits -= self._bits & int(mask)"),
    ],
    "normalize using integer addition": [
        ("self._bits = int(initial)", "self._bits = initial + 0"),
        ("self._bits &= ~int(mask)", "self._bits &= ~(mask + 0)"),
    ],
    "apply the removal only before the first attempt": [
        ("        for _ in range(attempts):\n            self._clear_bits(mask)", "        if attempts > 0:\n            self._clear_bits(mask)\n        for _ in range(attempts):"),
    ],
    "apply the removal twice per attempt": [
        ("self._bits &= ~int(mask)", "self._bits &= ~int(mask)\n        self._bits &= ~int(mask)"),
    ],
    "different callable import": [
        ("from collections.abc import Callable", "from typing import Callable"),
    ],
    "exhaustion raises a different synchronous exception": [
        ("        return False", "        raise RuntimeError('confirmation not received')"),
    ],
    "return value is outside the state claim": [
        ("            return True", "            return False"),
    ],
    "slots restrict representation without changing state": [
        ("class FeatureFlags:", 'class FeatureFlags:\n    __slots__ = ("_bits",)'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
