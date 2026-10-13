WEAKENED: dict[str, list[tuple[str, str]]] = {
    "initial_state_lost": [
        ("self._position = int(position)", "self._position = 0"),
    ],
    "negative_initial_clamped": [
        ("self._position = int(position)", "self._position = max(0, int(position))"),
    ],
    "backward_move": [
        ("max(0, target - self._position)", "target - self._position"),
    ],
    "absolute_residual": [
        ("max(0, target - self._position)", "abs(target - self._position)"),
    ],
    "retries_credit_target_again": [
        ("max(0, target - self._position)", "max(0, target)"),
    ],
    "cached_residual_reused": [
        (
            "target = int(position)",
            "target = int(position)\n        residual = max(0, target - self._position)",
        ),
        ("self._advance(target)", "self._position += residual"),
    ],
    "at_least_one_attempt": [
        ("range(attempts)", "range(max(1, attempts))"),
    ],
    "zero_count_still_updates": [
        (
            "for _ in range(attempts):",
            "if attempts == 0:\n            self._advance(target)\n        for _ in range(attempts):",
        ),
    ],
    "negative_count_still_updates": [
        (
            "for _ in range(attempts):",
            "if attempts < 0:\n            self._advance(target)\n        for _ in range(attempts):",
        ),
    ],
    "absolute_target": [
        ("target = int(position)", "target = abs(int(position))"),
    ],
    "float_rounding": [
        ("target = int(position)", "target = int(float(position))"),
    ],
    "uint64_truncation": [
        ("target = int(position)", "target = int(position) & ((1 << 64) - 1)"),
    ],
    "plain_int_only_target": [
        (
            "target = int(position)",
            "if type(position) is not int:\n            return False\n        target = int(position)",
        ),
    ],
    "plain_int_only_initial": [
        (
            "self._position = int(position)",
            "self._position = int(position) if type(position) is int else 0",
        ),
    ],
    "plain_int_only_attempts": [
        (
            "target = int(position)",
            "if type(attempts) is not int:\n            return False\n        target = int(position)",
        ),
    ],
    "callback_sees_old_position": [
        ("            self._advance(target)\n", ""),
        ("                acknowledge()", "                acknowledge()\n                self._advance(target)"),
    ],
    "rollback_after_timeout": [
        ("target = int(position)", "target = int(position)\n        before = self._position"),
        ("except TimeoutError:\n                continue", "except TimeoutError:\n                self._position = before\n                continue"),
    ],
    "rollback_after_other_exception": [
        ("target = int(position)", "target = int(position)\n        before = self._position"),
        (
            "                continue\n            return True",
            "                continue\n            except BaseException:\n                self._position = before\n                raise\n            return True",
        ),
    ],
    "single_attempt_skipped": [
        (
            "target = int(position)",
            "if attempts == 1:\n            return False\n        target = int(position)",
        ),
    ],
    "default_attempts_zero": [
        ("attempts: int = 3", "attempts: int = 0"),
    ],
    "reset_between_public_calls": [
        ("target = int(position)", "self._position = 0\n        target = int(position)"),
    ],
    "only_first_success_can_advance": [
        (
            "target = int(position)",
            "if getattr(self, '_finished', False):\n            return True\n        target = int(position)",
        ),
        ("            return True\n        return False", "            self._finished = True\n            return True\n        return False"),
    ],
    "second_retry_drifts": [
        ("for _ in range(attempts):", "for retry in range(attempts):"),
        ("self._advance(target)", "self._advance(target + (retry >= 2))"),
    ],
    "equal_target_increments": [
        (
            "self._position += max(0, target - self._position)",
            "self._position += 1 if target == self._position else max(0, target - self._position)",
        ),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "max_assignment": [
        ("self._position += max(0, target - self._position)", "self._position = max(self._position, target)"),
    ],
    "conditional_assignment": [
        (
            "self._position += max(0, target - self._position)",
            "if target > self._position:\n            self._position = target",
        ),
    ],
    "equivalent_minimum": [
        ("self._position += max(0, target - self._position)", "self._position -= min(0, self._position - target)"),
    ],
    "preserve_int_subtypes": [
        ("self._position = int(position)", "self._position = position"),
        ("target = int(position)", "target = position"),
    ],
    "retry_more_exception_types": [
        ("except TimeoutError:", "except BaseException:"),
    ],
    "propagate_timeout_with_other_type": [
        ("except TimeoutError:\n                continue", "except TimeoutError as error:\n                raise RuntimeError('ack failed') from error"),
    ],
    "different_return_value": [
        ("return True", "return None"),
        ("return False", "return None"),
    ],
    "typing_import": [
        ("from collections.abc import Callable", "from typing import Callable"),
    ],
    "exhaustion_raises": [
        ("        return False", "        raise RuntimeError('acknowledgement exhausted')"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
