VALIDATION = '    if length < 0 or start < 0 or start > stop or stop > length:\n        raise ValueError("invalid selection")'
RESULT = "    left = length - stop\n    right = length - start\n    return left, right"

WEAKENED = {
    "negative length accepted": [
        (VALIDATION, '    if length >= 0 and (start < 0 or start > stop or stop > length):\n        raise ValueError("invalid selection")'),
    ],
    "negative start accepted": [
        ("length < 0 or start < 0 or start > stop or stop > length",
         "length < 0 or start > stop or stop > length"),
    ],
    "reversed selection accepted": [
        ("length < 0 or start < 0 or start > stop or stop > length",
         "length < 0 or start < 0 or stop > length"),
    ],
    "stop beyond document accepted": [
        ("length < 0 or start < 0 or start > stop or stop > length",
         "length < 0 or start < 0 or start > stop"),
    ],
    "assert validation disappears under optimization": [
        (VALIDATION, '    assert length >= 0 and 0 <= start <= stop <= length, "invalid selection"'),
    ],
    "empty document rejected": [("length < 0", "length <= 0")],
    "zero start rejected": [("start < 0", "start <= 0")],
    "empty selections rejected": [("start > stop", "start >= stop")],
    "terminal boundary rejected": [("stop > length", "stop >= length")],
    "left boundary treated as character index": [
        ("left = length - stop", "left = length - stop - 1"),
    ],
    "right boundary treated as character index": [
        ("right = length - start", "right = length - start - 1"),
    ],
    "both boundaries treated as character indices": [
        ("left = length - stop", "left = length - stop - 1"),
        ("right = length - start", "right = length - start - 1"),
    ],
    "left boundary expanded": [
        ("left = length - stop", "left = length - stop + 1"),
    ],
    "right boundary expanded": [
        ("right = length - start", "right = length - start + 1"),
    ],
    "endpoints swapped": [("return left, right", "return right, left")],
    "selection kept in original coordinates": [
        ("return left, right", "return start, stop"),
    ],
    "empty cursor reset to origin": [
        ("return left, right", "return (0, 0) if start == stop else (left, right)"),
    ],
    "empty cursor left at old position": [
        ("return left, right", "return (start, stop) if start == stop else (left, right)"),
    ],
    "large boundaries rounded through float": [
        ("left = length - stop", "left = int(float(length) - float(stop))"),
        ("right = length - start", "right = int(float(length) - float(start))"),
    ],
    "boundaries truncated to 64 bits": [
        ("return left, right", "return left % (2**64), right % (2**64)"),
    ],
    "large integers rejected": [
        ("if length < 0", "if length.bit_length() > 64 or length < 0"),
    ],
    "ordinary integer subtypes rejected": [
        ("if length < 0", "if any(type(v) is not int for v in (length, start, stop)) or length < 0"),
    ],
    "bool arguments rejected": [
        ("if length < 0", "if any(isinstance(v, bool) for v in (length, start, stop)) or length < 0"),
    ],
    "enum arguments rejected": [
        ("if length < 0", 'if any(hasattr(v, "name") for v in (length, start, stop)) or length < 0'),
    ],
    "floating point boundaries returned": [
        ("return left, right", "return float(left), float(right)"),
    ],
    "wrong return container": [("return left, right", "return [left, right]")],
}

SAFE = {
    "different rejection exception": [
        ('raise ValueError("invalid selection")', 'raise RuntimeError("invalid selection")'),
    ],
    "equivalent chained validation": [
        ("length < 0 or start < 0 or start > stop or stop > length",
         "not (length >= 0 and 0 <= start <= stop <= length)"),
    ],
    "exact additive arithmetic": [
        ("left = length - stop", "left = length + (-stop)"),
        ("right = length - start", "right = length + (-start)"),
    ],
    "right edge derived from preserved width": [
        ("right = length - start", "right = left + (stop - start)"),
    ],
    "temporary list with tuple result": [
        (RESULT, "    boundaries = [length - stop, length - start]\n    return tuple(boundaries)"),
    ],
    "canonicalize ordinary int subtypes": [
        ("    if length < 0", "    length, start, stop = map(int, (length, start, stop))\n    if length < 0"),
    ],
    "future annotations import": [
        ("\n\ndef reflect_selection", "\n\nfrom __future__ import annotations\n\ndef reflect_selection"),
    ],
    "modular negation expressed using bitwise complement": [
        ("left = length - stop", "left = length + ~stop + 1"),
        ("right = length - start", "right = length + ~start + 1"),
    ],
}

RACY = {}
