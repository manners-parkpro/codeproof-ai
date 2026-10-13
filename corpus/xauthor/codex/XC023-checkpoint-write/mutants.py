WEAKENED: dict[str, list[tuple[str, str]]] = {
    "retry_cursor_not_restored": [
        ("        self._stream.seek(checkpoint)\n", ""),
    ],
    "retry_uses_current_end": [
        ("self._stream.seek(checkpoint)", "self._stream.seek(0, 2)"),
    ],
    "relative_checkpoint": [
        ("self._stream.seek(checkpoint)", "self._stream.seek(checkpoint, 1)"),
    ],
    "empty_origin_not_restored": [
        ("        self._stream.seek(checkpoint)",
         "        if checkpoint:\n            self._stream.seek(checkpoint)"),
    ],
    "existing_prefix_overwritten": [
        ("self._stream.seek(checkpoint)", "self._stream.seek(0)"),
    ],
    "constructor_cursor_used_as_end": [
        ("checkpoint = self._stream.seek(0, 2)", "checkpoint = self._stream.tell()"),
    ],
    "initial_contents_discarded": [
        ("BytesIO(initial)", "BytesIO()"),
    ],
    "constructor_subtype_discarded": [
        ("BytesIO(initial)", "BytesIO(initial if type(initial) is bytes else b'')"),
    ],
    "payload_subtype_skipped": [
        ("self._stream.write(payload)",
         "self._stream.write(payload if type(payload) is bytes else b'')"),
    ],
    "payload_truncated_at_block_boundary": [
        ("self._stream.write(payload)", "self._stream.write(payload[:4096])"),
    ],
    "trailing_zero_bytes_stripped": [
        ("self._stream.write(payload)", "self._stream.write(payload.rstrip(b'\\x00'))"),
    ],
    "empty_payload_gets_marker": [
        ("self._stream.write(payload)", "self._stream.write(payload or b'\\x00')"),
    ],
    "zero_attempts_still_write": [
        ("range(attempts)", "range(1 if attempts == 0 else attempts)"),
    ],
    "negative_attempts_still_write": [
        ("range(attempts)", "range(abs(attempts))"),
    ],
    "integer_subtypes_skipped": [
        ("range(attempts)", "range(attempts if type(attempts) is int else 0)"),
    ],
    "large_attempts_narrowed": [
        ("range(attempts)", "range(attempts % (2**32) if attempts > 0 else 0)"),
    ],
    "timeout_undoes_completed_write": [
        ("            except TimeoutError:\n                continue",
         "            except TimeoutError:\n                self._stream.truncate(checkpoint)\n                continue"),
    ],
    "other_exception_undoes_completed_write": [
        ("            return True",
         "            except BaseException:\n                self._stream.truncate(checkpoint)\n                raise\n            return True"),
    ],
    "later_calls_reuse_constructor_end": [
        ("        self._stream = BytesIO(initial)",
         "        self._stream = BytesIO(initial)\n        self._start = len(initial)"),
        ("checkpoint = self._stream.seek(0, 2)", "checkpoint = self._start"),
    ],
    "equal_payload_in_later_call_is_dropped": [
        ("        self._stream = BytesIO(initial)",
         "        self._stream = BytesIO(initial)\n        self._previous = None"),
        ("        checkpoint = self._stream.seek(0, 2)",
         "        if payload == self._previous:\n            return False\n        self._previous = payload\n        checkpoint = self._stream.seek(0, 2)"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "checkpoint_from_length": [
        ("checkpoint = self._stream.seek(0, 2)",
         "checkpoint = len(self._stream.getvalue())"),
    ],
    "explicit_absolute_seek": [
        ("self._stream.seek(checkpoint)", "self._stream.seek(checkpoint, 0)"),
    ],
    "bytesio_import_alias": [
        ("from io import BytesIO", "import io"),
        ("BytesIO(initial)", "io.BytesIO(initial)"),
    ],
    "buffer_view_write": [
        ("self._stream.write(payload)", "self._stream.write(memoryview(payload))"),
    ],
    "propagate_another_error_after_timeout": [
        ("            except TimeoutError:\n                continue",
         "            except TimeoutError as error:\n                raise RuntimeError('unconfirmed') from error"),
    ],
    "copy_snapshot": [
        ("return self._stream.getvalue()", "return bytes(bytearray(self._stream.getvalue()))"),
    ],
    "restore_cursor_after_each_write": [
        ("        self._stream.write(payload)",
         "        self._stream.write(payload)\n        self._stream.seek(checkpoint)"),
    ],
    "reject_nonpositive_attempts": [
        ("        checkpoint = self._stream.seek(0, 2)",
         "        if attempts <= 0:\n            raise ValueError('attempts')\n        checkpoint = self._stream.seek(0, 2)"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}

COVERAGE = {
    "all_initial_contents": (
        "SEEDS; initial snapshot",
        "initial_contents_discarded; constructor_subtype_discarded",
    ),
    "all_reachable_sequential_states": (
        "attack sequential steps; equal payload twice; append after exception",
        "later_calls_reuse_constructor_end; equal_payload_in_later_call_is_dropped",
    ),
    "empty_and_nonempty_origin": (
        "SEEDS; REPLIES with repeated timeouts",
        "empty_origin_not_restored; existing_prefix_overwritten",
    ),
    "all_payload_contents_and_sizes": (
        "PAYLOADS; empty; embedded and trailing zeros; all byte values; above 4096",
        "empty_payload_gets_marker; trailing_zero_bytes_stripped; payload_truncated_at_block_boundary",
    ),
    "ordinary_subtypes": (
        "Payload; Attempts; RetryCount; bool",
        "payload_subtype_skipped; integer_subtypes_skipped",
    ),
    "all_integer_attempt_counts": (
        "COUNTS; huge negative; zero; huge positive with early acknowledgement",
        "zero_attempts_still_write; negative_attempts_still_write; large_attempts_narrowed",
    ),
    "acknowledgement_success_exception_exhaustion": (
        "REPLIES; immediate success; repeated timeouts; TimeoutError subtype; BaseException",
        "timeout_undoes_completed_write; other_exception_undoes_completed_write",
    ),
    "same_fixed_interval_for_each_retry": (
        "REPLIES with multiple retries; nonempty seed",
        "retry_cursor_not_restored; retry_uses_current_end; relative_checkpoint; constructor_cursor_used_as_end",
    ),
    "outside_claim_choices": (
        "state-only oracle; no source inspection; no exception class requirement",
        "all SAFE variants",
    ),
}
