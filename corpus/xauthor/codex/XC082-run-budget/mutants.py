"""주장 축별 변이 - 누적량과 경계, 값 보존, 타입 및 호출 상태를 각각 약화한다."""

WEAKENED = {
    "single run upper boundary": [
        ("if count > remaining:", "if count > remaining + 1:"),
    ],
    "aggregate budget replaced by per-run limit": [
        ("if count > remaining:", "if count > 4096:"),
    ],
    "unit runs evade debit": [
        ("remaining -= count", "remaining -= count if count != 1 else 0"),
    ],
    "exact capacity rejected": [
        ("if count > remaining:", "if count >= remaining:"),
    ],
    "zero count rejected": [
        ("or count < 0:", "or count <= 0:"),
    ],
    "empty input rejected": [
        ("    remaining = 4096", "    if not runs:\n        raise ValueError(\"empty\")\n    remaining = 4096"),
    ],
    "negative count restores budget": [
        ("if not 0 <= value <= 255 or count < 0:", "if not 0 <= value <= 255:"),
    ],
    "zero run bypasses byte validation": [
        ("if not 0 <= value <= 255 or count < 0:", "if (count and not 0 <= value <= 255) or count < 0:"),
    ],
    "full prefix bypasses invalid suffix": [
        ("    for value, count in runs:", "    for value, count in runs:\n        if remaining == 0:\n            break"),
    ],
    "lower byte boundary rejected": [
        ("not 0 <= value <= 255", "not 0 < value <= 255"),
    ],
    "upper byte boundary rejected": [
        ("not 0 <= value <= 255", "not 0 <= value < 255"),
    ],
    "run order reversed": [
        ("return _expand_runs(accepted)", "return _expand_runs(accepted[::-1])"),
    ],
    "zero byte replaced": [
        ("accepted.append((value, count))", "accepted.append((value or 1, count))"),
    ],
    "repeated count shortened": [
        ("accepted.append((value, count))", "accepted.append((value, max(0, count - 1)))"),
    ],
    "ordinary integer subclasses rejected": [
        ("    for value, count in runs:", "    for value, count in runs:\n        if type(value) is not int or type(count) is not int:\n            raise TypeError(\"exact integers required\")"),
    ],
    "bool rejected": [
        ("    for value, count in runs:", "    for value, count in runs:\n        if isinstance(value, bool) or isinstance(count, bool):\n            raise TypeError(\"bool\")"),
    ],
    "list subclass rejected": [
        ("    remaining = 4096", "    if type(runs) is not list:\n        raise TypeError(\"exact list\")\n    remaining = 4096"),
    ],
    "input cleared after validation": [
        ("    return _expand_runs(accepted)", "    runs.clear()\n    return _expand_runs(accepted)"),
    ],
    "previous budget reused": [
        ("remaining = 4096", "remaining = globals().get(\"_remaining\", 4096)"),
        ("    return _expand_runs(accepted)", "    globals()[\"_remaining\"] = remaining\n    return _expand_runs(accepted)"),
    ],
    "returned buffer shared across calls": [
        ("    return bytearray(value for value, count in runs for _ in range(count))", "    global _cache\n    if \"_cache\" not in globals():\n        _cache = bytearray(value for value, count in runs for _ in range(count))\n    return _cache"),
    ],
    "assert budget disappears in optimized Python": [
        ("        if count > remaining:\n            raise ValueError(\"record too large\")", "        assert count <= remaining"),
    ],
}

SAFE = {
    "different synchronous exception": [
        ("raise ValueError(\"record too large\")", "raise RuntimeError(\"capacity\")"),
        ("raise ValueError(\"invalid run\")", "raise TypeError(\"run\")"),
    ],
    "tuple passed to expansion": [
        ("return _expand_runs(accepted)", "return _expand_runs(tuple(accepted))"),
    ],
    "comparison reversed": [
        ("if count > remaining:", "if remaining < count:"),
    ],
    "debit before budget test": [
        ("        if count > remaining:\n            raise ValueError(\"record too large\")\n        remaining -= count", "        remaining -= count\n        if remaining < 0:\n            raise ValueError(\"record too large\")"),
    ],
    "explicit builtins import": [
        ("    return bytearray(value for value, count in runs for _ in range(count))", "    import builtins\n    return builtins.bytearray(value for value, count in runs for _ in range(count))"),
    ],
    "equivalent materialization": [
        ("    return bytearray(value for value, count in runs for _ in range(count))", "    result = bytearray()\n    for value, count in runs:\n        result.extend(bytes([value]) * count)\n    return result"),
    ],
    "input snapshot": [
        ("    for value, count in runs:", "    for value, count in tuple(runs):"),
    ],
}

RACY = {}
