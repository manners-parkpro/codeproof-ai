AXES = {
    "empty_and_size": "batch: 0, 1, 2, 3, 8, 65, 257 -> empty_drain_fails, size_cap_64",
    "every_entry_and_order": "batch: distinct labels and every failure position -> fifo_order, oldest_lost, newest_lost",
    "every_synchronous_failure": "batch: Exception, direct BaseException, cancellation, termination, custom, mixed groups -> corresponding escape mutants",
    "result_independence": "batch: falsey and truthy ordinary return values -> truthy_result_stops, falsey_result_stops",
    "exactly_once": "batch: successful callbacks and repeated empty drains -> success_called_twice, consumed_entries_retried",
    "repeated_registration": "duplicate_registrations: one callable registered three times -> duplicate_registrations_coalesced",
    "reuse": "batch: drain empty repeatedly then register again -> refill_discarded",
    "new_items": "registration_during_drain: new callbacks added before return or exception -> new_registrations_cleared_at_exit",
    "nested_drain": "registration_during_drain(nested=True) -> nonempty_reentry_ignored",
    "empty_nested_drain": "empty_reentry: no new registrations -> empty_reentry_replays_current_batch",
    "safe_oracle": "SAFE changes preserve detached batches, reverse order, per-callback absorption, and fresh registrations; attack checks public observations only"
}

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "failure_stops_remaining_cleanup": [
        ("        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n", "        try:\n            for callback in reversed(callbacks):\n                callback()\n        except BaseException:\n            pass\n"),
    ],
    "ordinary_exception_only": [
        ("except BaseException:", "except Exception:"),
    ],
    "interrupt_escapes": [
        ("except BaseException:", "except KeyboardInterrupt:\n                raise\n            except BaseException:"),
    ],
    "exit_escapes": [
        ("except BaseException:", "except SystemExit:\n                raise\n            except BaseException:"),
    ],
    "generator_exit_escapes": [
        ("except BaseException:", "except GeneratorExit:\n                raise\n            except BaseException:"),
    ],
    "group_escapes": [
        ("except BaseException:", "except BaseExceptionGroup:\n                raise\n            except BaseException:"),
    ],
    "cancellation_escapes": [
        ("from collections.abc import Callable", "from collections.abc import Callable\nfrom asyncio import CancelledError"),
        ("except BaseException:", "except CancelledError:\n                raise\n            except BaseException:"),
    ],
    "empty_drain_fails": [
        ("        for callback in reversed(callbacks):", "        if not callbacks:\n            raise ValueError('empty')\n        for callback in reversed(callbacks):"),
    ],
    "fifo_order": [
        ("reversed(callbacks)", "iter(callbacks)"),
    ],
    "size_cap_64": [
        ("reversed(callbacks)", "reversed(callbacks[:64])"),
    ],
    "oldest_lost": [
        ("reversed(callbacks)", "reversed(callbacks[1:])"),
    ],
    "newest_lost": [
        ("reversed(callbacks)", "reversed(callbacks[:-1])"),
    ],
    "success_called_twice": [
        ("                callback()", "                callback()\n                callback()"),
    ],
    "truthy_result_stops": [
        ("                callback()", "                if callback():\n                    break"),
    ],
    "falsey_result_stops": [
        ("                callback()", "                if not callback():\n                    break"),
    ],
    "duplicate_registrations_coalesced": [
        ("        self._callbacks.append(callback)", "        if callback not in self._callbacks:\n            self._callbacks.append(callback)"),
    ],
    "consumed_entries_retried": [
        ("        self._callbacks = []", "        self._callbacks = callbacks"),
    ],
    "refill_discarded": [
        ("        self._callbacks.append(callback)", "        if not getattr(self, '_drained', False):\n            self._callbacks.append(callback)"),
        ("        callbacks = self._callbacks", "        self._drained = True\n        callbacks = self._callbacks"),
    ],
    "new_registrations_cleared_at_exit": [
        ("        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n", "        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n        self._callbacks.clear()\n"),
    ],
    "nonempty_reentry_ignored": [
        ("        callbacks = self._callbacks", "        if getattr(self, '_draining', False):\n            return\n        self._draining = True\n        callbacks = self._callbacks"),
        ("        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n", "        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n        self._draining = False\n"),
    ],
    "empty_reentry_replays_current_batch": [
        ("        self._callbacks = []", "        self._callbacks = []\n        if not callbacks and hasattr(self, '_active'):\n            callbacks = self._active\n        previous = getattr(self, '_active', [])\n        self._active = callbacks"),
        ("        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n", "        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n        self._active = previous\n"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "immutable_snapshot": [
        ("        callbacks = self._callbacks", "        callbacks = tuple(self._callbacks)"),
    ],
    "snapshot_then_clear": [
        ("        callbacks = self._callbacks\n        self._callbacks = []", "        callbacks = tuple(self._callbacks)\n        self._callbacks.clear()"),
    ],
    "slice_order": [
        ("reversed(callbacks)", "callbacks[::-1]"),
    ],
    "deque_storage": [
        ("from collections.abc import Callable", "from collections.abc import Callable\nfrom collections import deque"),
        ("        self._callbacks: list[Callable[[], object]] = []", "        self._callbacks: deque[Callable[[], object]] = deque()"),
        ("        self._callbacks = []", "        self._callbacks = deque()"),
    ],
    "explicit_continue": [
        ("            except BaseException:\n                pass", "            except BaseException:\n                continue"),
    ],
    "split_handlers": [
        ("            except BaseException:\n                pass", "            except Exception:\n                pass\n            except BaseException:\n                pass"),
    ],
    "bare_handler": [
        ("            except BaseException:", "            except:"),
    ],
    "pop_detached_batch": [
        ("        for callback in reversed(callbacks):", "        while callbacks:\n            callback = callbacks.pop()"),
    ],
    "helper_contains_absorption": [
        ("        for callback in reversed(callbacks):\n            try:\n                callback()\n            except BaseException:\n                pass\n", "        def invoke(callback: Callable[[], object]) -> None:\n            try:\n                callback()\n            except BaseException:\n                pass\n\n        for callback in reversed(callbacks):\n            invoke(callback)\n"),
    ],
    "baseexception_import_alias": [
        ("from collections.abc import Callable", "from collections.abc import Callable\nfrom builtins import BaseException as CleanupFailure"),
        ("except BaseException:", "except CleanupFailure:"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
