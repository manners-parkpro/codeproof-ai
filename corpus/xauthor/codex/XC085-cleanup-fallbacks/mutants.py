WEAKENED: dict[str, list[tuple[str, str]]] = {
    "empty_is_error": [
        ("    failures: list[BaseException] = []", "    if not strategies:\n        raise ValueError('empty')\n    failures: list[BaseException] = []"),
    ],
    "truncate": [
        ("for cleanup in strategies:", "for cleanup in strategies[:16]:"),
    ],
    "reverse": [
        ("for cleanup in strategies:", "for cleanup in reversed(strategies):"),
    ],
    "deduplicate": [
        ("for cleanup in strategies:", "for cleanup in dict.fromkeys(strategies):"),
    ],
    "keep_going": [
        ("        else:\n            return None", "        else:\n            pass"),
    ],
    "skip_first": [
        ("for cleanup in strategies:", "for cleanup in strategies[1:]:"),
    ],
    "truthy_only": [
        ("            cleanup()", "            value = cleanup()"),
        ("        else:\n            return None", "        else:\n            if value:\n                return None"),
    ],
    "return_payload": [
        ("            cleanup()", "            value = cleanup()"),
        ("        else:\n            return None", "        else:\n            return value"),
    ],
    "exception_only": [
        ("except BaseException as error:", "except Exception as error:"),
    ],
    "stop_after_failure": [
        ("            failures.append(error)", "            failures.append(error)\n            break"),
    ],
    "swallow_all": [
        ("    if failures:", "    if False and failures:"),
    ],
    "swallow_single": [
        ("    if failures:", "    if len(failures) > 1:"),
    ],
    "drop_last": [
        ('BaseExceptionGroup("All cleanup strategies failed", failures)', 'BaseExceptionGroup("All cleanup strategies failed", failures[:-1] or failures)'),
    ],
    "reverse_errors": [
        ('BaseExceptionGroup("All cleanup strategies failed", failures)', 'BaseExceptionGroup("All cleanup strategies failed", failures[::-1])'),
    ],
    "deduplicate_errors": [
        ("            failures.append(error)", "            if error not in failures:\n                failures.append(error)"),
    ],
    "clone_error": [
        ("            failures.append(error)", "            failures.append(RuntimeError(str(error)))"),
    ],
    "flatten_group": [
        ("            failures.append(error)", "            failures.extend(error.exceptions if isinstance(error, BaseExceptionGroup) else [error])"),
    ],
    "persistent_failures": [
        ("    failures: list[BaseException] = []", "    failures = getattr(cleanup_with_fallback, '_failures', [])\n    cleanup_with_fallback._failures = failures"),
    ],
    "exact_tuple_only": [
        ("    failures: list[BaseException] = []", "    if type(strategies) is not tuple:\n        raise TypeError('tuple required')\n    failures: list[BaseException] = []"),
    ],
    "single_failure_unwrapped": [
        ("    if failures:", "    if len(failures) == 1:\n        raise failures[0]\n    if failures:"),
    ],
    "base_group_rejected": [
        ('raise BaseExceptionGroup("All cleanup strategies failed", failures)', 'raise ExceptionGroup("All cleanup strategies failed", failures)'),
    ],
    "optimization_loses_guard": [
        ('        raise BaseExceptionGroup("All cleanup strategies failed", failures)', '        assert _propagate(failures)'),
        ('from collections.abc import Callable', 'from collections.abc import Callable\n\ndef _propagate(failures):\n    raise BaseExceptionGroup("All cleanup strategies failed", failures)'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different_message": [
        ('"All cleanup strategies failed"', '"No alternative returned normally"'),
    ],
    "explicit_cause": [
        ('raise BaseExceptionGroup("All cleanup strategies failed", failures)', 'raise BaseExceptionGroup("All cleanup strategies failed", failures) from failures[0]'),
    ],
    "no_context": [
        ('raise BaseExceptionGroup("All cleanup strategies failed", failures)', 'raise BaseExceptionGroup("All cleanup strategies failed", failures) from None'),
    ],
    "tuple_storage": [
        ("    failures: list[BaseException] = []", "    failures: tuple[BaseException, ...] = ()"),
        ("            failures.append(error)", "            failures += (error,)"),
    ],
    "deque_storage": [
        ("from collections.abc import Callable", "from collections.abc import Callable\nfrom collections import deque"),
        ("    failures: list[BaseException] = []", "    failures = deque()"),
    ],
    "extend_singleton": [
        ("            failures.append(error)", "            failures.extend((error,))"),
    ],
    "index_iteration": [
        ("    for cleanup in strategies:", "    for index in range(len(strategies)):\n        cleanup = strategies[index]"),
    ],
    "typing_import": [
        ("from collections.abc import Callable", "from typing import Callable"),
    ],
    "explicit_size": [
        ("    if failures:", "    if len(failures) != 0:"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
