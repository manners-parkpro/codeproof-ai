WEAKENED: dict[str, list[tuple[str, str]]] = {
    "reject_zero_ticks": [
        ("if any(", "if any(tick == 0 for tick in ticks) or any("),
    ],
    "reject_tick_subtypes": [
        ("if any(", "if any(type(tick) is not int for tick in ticks) or any("),
    ],
    "reject_list_subtypes": [
        ("if any(", "if type(ticks) is not list or any("),
    ],
    "float_zero_result": [
        ("return [tick * target_hz // source_hz for tick in ticks]", "return [0.0 if tick == 0 else tick * target_hz // source_hz for tick in ticks]"),
    ],
    "source_negative": [
        ("source_hz <= 0", "source_hz == 0"),
    ],
    "target_negative": [
        ("target_hz <= 0", "target_hz == 0"),
    ],
    "source_zero_empty": [
        ("source_hz <= 0", "source_hz < 0"),
    ],
    "target_zero": [
        ("target_hz <= 0", "target_hz < 0"),
    ],
    "empty_skips_rates": [
        ("    _validate_ticks(ticks, source_hz, target_hz)", "    if not ticks:\n        return []\n    _validate_ticks(ticks, source_hz, target_hz)"),
    ],
    "all_instead_of_any": [
        ("if any(", "if ticks and all("),
    ],
    "only_first": [
        ("for tick in ticks):", "for tick in ticks[:1]):"),
    ],
    "only_last": [
        ("for tick in ticks):", "for tick in ticks[-1:]):"),
    ],
    "bounded_scan": [
        ("for tick in ticks):", "for tick in ticks[:64]):"),
    ],
    "skip_negative_ticks": [
        ("for tick in ticks):", "for tick in ticks if tick >= 0):"),
    ],
    "forget_target_factor": [
        ("(tick * target_hz) % source_hz", "tick % source_hz"),
    ],
    "reverse_divisor": [
        ("(tick * target_hz) % source_hz", "(tick * source_hz) % target_hz"),
    ],
    "float_integrality": [
        ("(tick * target_hz) % source_hz != 0", "not (tick * target_hz / source_hz).is_integer()"),
    ],
    "arbitrary_magnitude_limit": [
        ("if any(", "if any(abs(tick) > 2**63 - 1 for tick in ticks) or any("),
    ],
    "reject_negative_ticks": [
        ("if any(", "if any(tick < 0 for tick in ticks) or any("),
    ],
    "reject_subtypes": [
        ("    if source_hz <= 0 or target_hz <= 0:", "    if type(source_hz) is not int or type(target_hz) is not int:\n        raise ValueError('rates')\n    if source_hz <= 0 or target_hz <= 0:"),
    ],
    "sort_during_validation": [
        ("    if source_hz <= 0 or target_hz <= 0:", "    ticks.sort()\n    if source_hz <= 0 or target_hz <= 0:"),
    ],
    "mutate_on_rejection": [
        ("        raise ValueError(\"timestamp cannot be represented exactly\")", "        ticks.clear()\n        raise ValueError(\"timestamp cannot be represented exactly\")"),
    ],
    "assert_exactness": [
        ("    if any((tick * target_hz) % source_hz != 0 for tick in ticks):\n        raise ValueError(\"timestamp cannot be represented exactly\")", "    assert all((tick * target_hz) % source_hz == 0 for tick in ticks)"),
    ],
    "divide_before_multiply": [
        ("return [tick * target_hz // source_hz for tick in ticks]", "return [(tick // source_hz) * target_hz for tick in ticks]"),
    ],
    "round_through_float": [
        ("return [tick * target_hz // source_hz for tick in ticks]", "return [int(tick * target_hz / source_hz) for tick in ticks]"),
    ],
    "lose_order": [
        ("return [tick * target_hz // source_hz for tick in ticks]", "return sorted(tick * target_hz // source_hz for tick in ticks)"),
    ],
    "lose_multiplicity": [
        ("return [tick * target_hz // source_hz for tick in ticks]", "return list(dict.fromkeys(tick * target_hz // source_hz for tick in ticks))"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "exception_class": [
        ("raise ValueError(\"frequencies must be positive\")", "raise ArithmeticError(\"frequencies must be positive\")"),
        ("raise ValueError(\"timestamp cannot be represented exactly\")", "raise ArithmeticError(\"timestamp cannot be represented exactly\")"),
    ],
    "positive_conjunction": [
        ("source_hz <= 0 or target_hz <= 0", "not (source_hz > 0 and target_hz > 0)"),
    ],
    "all_exact": [
        ("any((tick * target_hz) % source_hz != 0 for tick in ticks)", "not all((tick * target_hz) % source_hz == 0 for tick in ticks)"),
    ],
    "eager_validation": [
        ("any((tick * target_hz) % source_hz != 0 for tick in ticks)", "any([(tick * target_hz) % source_hz != 0 for tick in ticks])"),
    ],
    "divmod_remainder": [
        ("(tick * target_hz) % source_hz", "divmod(tick * target_hz, source_hz)[1]"),
    ],
    "reduced_divisor": [
        ("from __future__ import annotations", "from __future__ import annotations\nfrom math import gcd"),
        ("(tick * target_hz) % source_hz", "tick % (source_hz // gcd(source_hz, target_hz))"),
    ],
    "explicit_loop": [
        ("    if any((tick * target_hz) % source_hz != 0 for tick in ticks):\n        raise ValueError(\"timestamp cannot be represented exactly\")", "    for tick in ticks:\n        if tick * target_hz % source_hz:\n            raise ValueError(\"inexact timestamp\")"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
}
