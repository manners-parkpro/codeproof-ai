GUARD = "    _validate_order(samples)"
CHECK = "any(left > right for left, right in zip(samples, samples[1:]))"
RESULT = "    return [bisect_right(samples, limit) for limit in limits]"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "skip order validation": [(GUARD, "    pass")],
    "empty limits skip rejection": [(GUARD, "    if limits:\n        _validate_order(samples)")],
    "only first adjacency": [(CHECK, "len(samples) > 1 and samples[0] > samples[1]")],
    "only endpoints": [(CHECK, "bool(samples) and samples[0] > samples[-1]")],
    "miss last adjacency": [(CHECK, "any(a > b for a, b in zip(samples[:-1], samples[1:-1]))")],
    "miss first adjacency": [(CHECK, "any(a > b for a, b in zip(samples[1:], samples[2:]))")],
    "reject equality": [(CHECK, "any(a >= b for a, b in zip(samples, samples[1:]))")],
    "negative values excluded from validation": [(CHECK, "any(a > b for a, b in zip(samples, samples[1:]) if a >= 0 and b >= 0)")],
    "large integer conversion overflows": [(CHECK, "any(float(a) > float(b) for a, b in zip(samples, samples[1:]))")],
    "finite integer precision lost": [(CHECK, "any((float(a) if abs(a) < 2**54 else a) > (float(b) if abs(b) < 2**54 else b) for a, b in zip(samples, samples[1:]))")],
    "validate only first 32 samples": [(GUARD, "    _validate_order(samples[:32])")],
    "reject empty samples": [(GUARD, "    if not samples:\n        raise ValueError('empty')\n    _validate_order(samples)")],
    "reject singleton samples": [(GUARD, "    if len(samples) == 1:\n        raise ValueError('singleton')\n    _validate_order(samples)")],
    "reject standard integer subtypes": [(GUARD, "    if any(type(x) is not int for x in samples + limits):\n        raise ValueError('type')\n    _validate_order(samples)")],
    "reject list subtypes": [(GUARD, "    if type(samples) is not list or type(limits) is not list:\n        raise ValueError('type')\n    _validate_order(samples)")],
    "sort invalid samples instead of rejecting": [(GUARD, "    samples.sort()")],
    "sort samples before rejection": [(GUARD, "    try:\n        _validate_order(samples)\n    except Exception:\n        samples.sort()\n        raise")],
    "strict threshold omits equal readings": [("from bisect import bisect_right", "from bisect import bisect_left as bisect_right")],
    "deduplicate readings": [(RESULT, "    return [bisect_right(sorted(set(samples)), limit) for limit in limits]")],
    "reorder thresholds": [(RESULT, "    return [bisect_right(samples, limit) for limit in sorted(limits)]")],
    "deduplicate thresholds": [(RESULT, "    return [bisect_right(samples, limit) for limit in dict.fromkeys(limits)]")],
    "empty samples drop requested counts": [(RESULT, "    return [bisect_right(samples, limit) for limit in limits] if samples else []")],
    "mutate samples after valid lookup": [(RESULT, "    result = [bisect_right(samples, limit) for limit in limits]\n    samples.clear()\n    return result")],
    "mutate limits after valid lookup": [(RESULT, "    result = [bisect_right(samples, limit) for limit in limits]\n    limits.clear()\n    return result")],
    "mutate limits before rejecting": [(GUARD, "    try:\n        _validate_order(samples)\n    except Exception:\n        limits.clear()\n        raise")],
    "reject aliased inputs": [(GUARD, "    if samples is limits:\n        raise ValueError('alias')\n    _validate_order(samples)")],
    "assert guard disappears under optimization": [("    if " + CHECK + ":\n        raise ValueError(\"samples must be nondecreasing\")", "    assert not " + CHECK)],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different rejection exception": [("raise ValueError(\"samples must be nondecreasing\")", "raise RuntimeError('order')")],
    "sorted equality validation": [(CHECK, "samples != sorted(samples)")],
    "indexed adjacent validation": [(CHECK, "any(samples[i - 1] > samples[i] for i in range(1, len(samples)))")],
    "inclusive comparison formulation": [(CHECK, "not all(a <= b for a, b in zip(samples, samples[1:]))")],
    "module import form": [("from bisect import bisect_right", "import bisect"), ("bisect_right(samples, limit)", "bisect.bisect_right(samples, limit)")],
    "linear count implementation": [(RESULT, "    return [sum(value <= limit for value in samples) for limit in limits]")],
    "copy samples before lookup": [(GUARD, "    samples = list(samples)\n    _validate_order(samples)")],
}

RACY: dict[str, list[tuple[str, str]]] = {}
