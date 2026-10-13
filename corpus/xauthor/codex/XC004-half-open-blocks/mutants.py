"""주장 축별 변이 - 거절 조건과 경계 및 정수 범위를 약화하고 동등한 구현을 대조한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "empty_interior": [
        ("    if start == stop:\n        return range(0)\n", ""),
    ],
    "empty_only_at_origin": [
        ("if start == stop:", "if start == stop == 0:"),
    ],
    "empty_only_on_block_boundary": [
        ("if start == stop:", "if start == stop and start % block_size == 0:"),
    ],
    "empty_unit_blocks": [
        ("return range(0)", "return range(1) if block_size == 1 else range(0)"),
    ],
    "negative_start": [
        ("start < 0 or stop < start or block_size <= 0", "stop < start or block_size <= 0"),
    ],
    "reversed_span": [
        ("start < 0 or stop < start or block_size <= 0", "start < 0 or block_size <= 0"),
    ],
    "negative_block_size": [
        ("block_size <= 0", "block_size == 0"),
    ],
    "zero_size_empty_span": [
        ("        raise ValueError(\"invalid byte span or block size\")",
         "        if block_size == 0 and start == stop:\n            return range(0)\n        raise ValueError(\"invalid byte span or block size\")"),
    ],
    "first_partial_block": [
        ("first = start // block_size", "first = (start + block_size - 1) // block_size"),
    ],
    "excluded_stop_boundary": [
        ("last = (stop - 1) // block_size", "last = stop // block_size"),
    ],
    "single_final_byte": [
        ("last = (stop - 1) // block_size", "last = (stop - 2) // block_size"),
    ],
    "missing_final_block": [
        ("return range(first, last + 1)", "return range(first, last)"),
    ],
    "skipped_middle_blocks": [
        ("return range(first, last + 1)", "return range(first, last + 1, 2)"),
    ],
    "descending_blocks": [
        ("return range(first, last + 1)", "return range(last, first - 1, -1)"),
    ],
    "float_rounding": [
        ("first = start // block_size", "first = int(start / block_size)"),
    ],
    "fixed_width_truncation": [
        ("last = (stop - 1) // block_size", "last = ((stop - 1) % (2**64)) // block_size"),
    ],
    "platform_length_limit": [
        ("return range(first, last + 1)", "result = range(first, last + 1)\n    len(result)\n    return result"),
    ],
    "boolean_rejected": [
        ("    if start < 0", "    if any(isinstance(v, bool) for v in (start, stop, block_size)):\n        raise ValueError(\"boolean\")\n    if start < 0"),
    ],
    "ordinary_subclass_rejected": [
        ("    if start < 0", "    if any(type(v) not in (int, bool) for v in (start, stop, block_size)):\n        raise ValueError(\"subclass\")\n    if start < 0"),
    ],
    "assert_validation": [
        ("    if start < 0 or stop < start or block_size <= 0:\n        raise ValueError(\"invalid byte span or block size\")",
         "    assert start >= 0 and stop >= start and block_size > 0"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different_rejection_exception": [
        ("raise ValueError(", "raise RuntimeError("),
    ],
    "equivalent_empty_range": [
        ("return range(0)", "return range(37, 37, 3)"),
    ],
    "exclusive_ceiling": [
        ("last = (stop - 1) // block_size\n    return range(first, last + 1)",
         "end, remainder = divmod(stop, block_size)\n    return range(first, end + bool(remainder))"),
    ],
    "integer_ceiling_identity": [
        ("last = (stop - 1) // block_size\n    return range(first, last + 1)",
         "end = -(-stop // block_size)\n    return range(first, end)"),
    ],
    "equivalent_validation": [
        ("start < 0 or stop < start or block_size <= 0", "not (0 <= start <= stop and 0 < block_size)"),
    ],
    "explicit_unit_step": [
        ("return range(first, last + 1)", "return range(first, last + 1, 1)"),
    ],
    "renamed_builtin_import": [
        ("\n\ndef blocks_for_span", "\n\nfrom builtins import range as block_range\n\n\ndef blocks_for_span"),
        ("return range(0)", "return block_range(0)"),
        ("return range(first, last + 1)", "return block_range(first, last + 1)"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
