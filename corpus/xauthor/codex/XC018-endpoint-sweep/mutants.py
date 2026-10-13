WEAKENED: dict[str, list[tuple[str, str]]] = {
    "stop_is_included": [
        ("events.sort()", "events.sort(key=lambda event: (event[0], -event[1]))"),
    ],
    "overlaps_capped": [("return peak", "return min(peak, 1)")],
    "empty_input_nonzero": [("peak = 0", "peak = 1")],
    "empty_interval_occupies": [
        ("if start == stop:\n            continue", "if start == stop:\n            stop += 1"),
    ],
    "negative_coordinates_rejected": [
        ("if start > stop:", "if start > stop or start < 0:"),
    ],
    "fixed_width_coordinates": [
        ("if start > stop:", "if start > stop or max(abs(start), abs(stop)) > 2**63 - 1:"),
    ],
    "float_coordinates": [
        ("events.sort()", "events.sort(key=lambda event: (float(event[0]), event[1]))"),
    ],
    "duplicate_events_lost": [("events.sort()", "events = sorted(set(events))")],
    "only_first_256": [("in spans:", "in spans[:256]:")],
    "input_order_used": [("    events.sort()\n", "")],
    "reversal_unchecked": [("if start > stop:", "if False:")],
    "only_first_reversal_checked": [
        ("if start > stop:", "if not events and start > stop:"),
    ],
    "bool_rejected": [
        ("if start > stop:", "if start > stop or isinstance(start, bool) or isinstance(stop, bool):"),
    ],
    "intenum_rejected": [
        ("events = []", "from enum import IntEnum\n    events = []"),
        ("if start > stop:", "if start > stop or isinstance(start, IntEnum) or isinstance(stop, IntEnum):"),
    ],
    "plain_int_subclass_rejected": [
        ("events = []", "from enum import IntEnum\n    events = []"),
        ("if start > stop:", "if start > stop or any(type(v) not in (int, bool) and not isinstance(v, IntEnum) for v in (start, stop)):"),
    ],
    "list_subclass_rejected": [
        ("events = []", "events = []\n    if type(spans) is not list:\n        raise TypeError('list required')"),
    ],
    "tuple_subclass_rejected": [
        ("events = []", "events = []\n    if any(type(span) is not tuple for span in spans):\n        raise TypeError('tuple required')"),
    ],
    "assert_reversal_check": [
        ("if start > stop:\n            raise ValueError(\"reversed interval\")", "assert start <= stop"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different_rejection_exception": [("raise ValueError(", "raise RuntimeError(")],
    "explicit_tie_order": [
        ("events.sort()", "events.sort(key=lambda event: (event[0], event[1]))"),
    ],
    "functional_sort": [("events.sort()", "events = sorted(events)")],
    "conditional_maximum": [
        ("peak = max(peak, active)", "if active > peak:\n            peak = active"),
    ],
    "empty_events_retained": [("        if start == stop:\n            continue\n", "")],
    "tuple_event_storage": [("events.sort()", "events = tuple(sorted(events))")],
}

RACY: dict[str, list[tuple[str, str]]] = {}
