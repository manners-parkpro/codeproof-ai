"""주장의 각 축을 약화하고 주장에 무관한 구현 선택은 바꾼다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "closed_stop": [
        ("last = bisect_left(ticks, stop)", "last = bisect_right(ticks, stop)"),
    ],
    "open_start": [
        ("first = bisect_left(ticks, start)", "first = bisect_right(ticks, start)"),
    ],
    "missing_reversed_check": [
        ('    if start > stop:\n        raise ValueError("reversed window")\n', ""),
    ],
    "empty_before_validation": [
        ("    if start > stop:", "    if not ticks:\n        return []\n    if start > stop:"),
    ],
    "missing_order_check": [
        ('    if any(a > b for a, b in zip(ticks, ticks[1:])):\n        raise ValueError("unordered ticks")\n', ""),
    ],
    "unchecked_last_pair": [
        ("zip(ticks, ticks[1:])", "zip(ticks[:-2], ticks[1:-1])"),
    ],
    "reject_duplicates": [
        ("any(a > b for", "any(a >= b for"),
    ],
    "reject_empty_window": [
        ("if start > stop:", "if start >= stop:"),
    ],
    "empty_window_includes_one": [
        ("return ticks[first:last]", "return ticks[first:first + 1] if start == stop else ticks[first:last]"),
    ],
    "deduplicate": [
        ("return ticks[first:last]", "return sorted(set(ticks[first:last]))"),
    ],
    "reverse_result": [
        ("return ticks[first:last]", "return ticks[first:last][::-1]"),
    ],
    "invent_event": [
        ("return ticks[first:last]", "return ticks[first:last] or [start]"),
    ],
    "clamp_negative": [
        ("first = bisect_left(ticks, start)", "first = bisect_left(ticks, max(0, start))"),
    ],
    "float_boundaries": [
        ("bisect_left(ticks, start)", "bisect_left(ticks, float(start))"),
        ("bisect_left(ticks, stop)", "bisect_left(ticks, float(stop))"),
    ],
    "truncate_long_window": [
        ("return ticks[first:last]", "return ticks[first:last][:256]"),
    ],
    "exact_integer_types": [
        ("    if start > stop:", '    if any(type(x) is not int for x in [start, stop, *ticks]):\n        raise TypeError("int required")\n    if start > stop:'),
    ],
    "exact_list_type": [
        ("    if start > stop:", '    if type(ticks) is not list:\n        raise TypeError("list required")\n    if start > stop:'),
    ],
    "mutate_on_success": [
        ("    return ticks[first:last]", "    result = ticks[first:last]\n    if ticks:\n        ticks.pop()\n    return result"),
    ],
    "mutate_on_rejection": [
        ('        raise ValueError("unordered ticks")', '        ticks.sort()\n        raise ValueError("unordered ticks")'),
    ],
    "assert_reversed": [
        ('    if start > stop:\n        raise ValueError("reversed window")', '    assert start <= stop, "reversed window"'),
    ],
    "assert_order": [
        ('    if any(a > b for a, b in zip(ticks, ticks[1:])):\n        raise ValueError("unordered ticks")', '    assert all(a <= b for a, b in zip(ticks, ticks[1:])), "unordered ticks"'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different_exception": [
        ('raise ValueError("reversed window")', 'raise RuntimeError("reversed window")'),
        ('raise ValueError("unordered ticks")', 'raise LookupError("unordered ticks")'),
    ],
    "module_import": [
        ("from bisect import bisect_left, bisect_right", "import bisect"),
        ("bisect_left(ticks, start)", "bisect.bisect_left(ticks, start)"),
        ("bisect_left(ticks, stop)", "bisect.bisect_left(ticks, stop)"),
    ],
    "linear_selection": [
        ("    first = bisect_left(ticks, start)\n    last = bisect_left(ticks, stop)\n    return ticks[first:last]", "    return [tick for tick in ticks if start <= tick < stop]"),
    ],
    "sorted_order_check": [
        ("any(a > b for a, b in zip(ticks, ticks[1:]))", "ticks != sorted(ticks)"),
    ],
    "equivalent_reversed_check": [
        ("if start > stop:", "if not start <= stop:"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
