"""주장별 변이 - 경계와 입력 양화를 약화하고 계약이 허용한 구현 변형은 보존한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "reversed_source_accepted": [
        ("if start > stop or cut_start > cut_stop:", "if cut_start > cut_stop:"),
    ],
    "reversed_cut_accepted": [
        ("if start > stop or cut_start > cut_stop:", "if start > stop:"),
    ],
    "empty_source_skips_cut_validation": [
        ("if start > stop or cut_start > cut_stop:", "if start != stop and (start > stop or cut_start > cut_stop):"),
    ],
    "optimized_assert_validation": [
        ("    if start > stop or cut_start > cut_stop:\n        raise ValueError(\"reversed span\")", "    assert start <= stop and cut_start <= cut_stop"),
    ],
    "negative_values_rejected": [
        ("    pieces = []", "    if min(start, stop, cut_start, cut_stop) < 0:\n        raise ValueError(\"negative endpoint\")\n    pieces = []"),
    ],
    "huge_values_rejected": [
        ("    pieces = []", "    if max(abs(start), abs(stop), abs(cut_start), abs(cut_stop)) > 2 ** 63:\n        raise ValueError(\"endpoint too large\")\n    pieces = []"),
    ],
    "bool_values_rejected": [
        ("    if start > stop or cut_start > cut_stop:", "    if any(isinstance(v, bool) for v in (start, stop, cut_start, cut_stop)):\n        raise ValueError(\"boolean endpoint\")\n    if start > stop or cut_start > cut_stop:"),
    ],
    "enum_values_rejected": [
        ("    if start > stop or cut_start > cut_stop:", "    from enum import IntEnum\n    if any(isinstance(v, IntEnum) for v in (start, stop, cut_start, cut_stop)):\n        raise ValueError(\"enum endpoint\")\n    if start > stop or cut_start > cut_stop:"),
    ],
    "plain_subtypes_rejected": [
        ("    if start > stop or cut_start > cut_stop:", "    from enum import IntEnum\n    if any(type(v) not in (int, bool) and not isinstance(v, IntEnum) for v in (start, stop, cut_start, cut_stop)):\n        raise ValueError(\"subclass endpoint\")\n    if start > stop or cut_start > cut_stop:"),
    ],
    "empty_source_emits_empty_piece": [
        ("    if start == stop:\n        return []", "    if start == stop:\n        return [(start, stop)]"),
    ],
    "empty_cut_erases_original": [
        ("    if cut_start == cut_stop:\n        return [(start, stop)]", "    if cut_start == cut_stop:\n        return []"),
    ],
    "empty_cut_splits_maximal_piece": [
        ("    if cut_start == cut_stop:\n        return [(start, stop)]", "    if False:\n        return [(start, stop)]"),
    ],
    "unclipped_prefix": [
        ("left_stop = min(stop, cut_start)", "left_stop = cut_start"),
    ],
    "unclipped_suffix": [
        ("right_start = max(start, cut_stop)", "right_start = cut_stop"),
    ],
    "prefix_loses_last_integer": [
        ("pieces.append((start, left_stop))", "pieces.append((start, left_stop - 1))"),
    ],
    "suffix_loses_first_integer": [
        ("pieces.append((right_start, stop))", "pieces.append((right_start + 1, stop))"),
    ],
    "empty_prefix_retained": [
        ("if start < left_stop:", "if start <= left_stop:"),
    ],
    "empty_suffix_retained": [
        ("if right_start < stop:", "if right_start <= stop:"),
    ],
    "reversed_result_order": [
        ("    return pieces", "    return pieces[::-1]"),
    ],
    "duplicate_pieces": [
        ("    return pieces", "    return pieces + pieces"),
    ],
    "retained_deleted_interior": [
        ("    return pieces", "    return [(start, stop)]"),
    ],
    "full_erasure_restores_original": [
        ("    return pieces", "    return pieces or [(start, stop)]"),
    ],
    "prefix_omitted": [
        ("pieces.append((start, left_stop))", "pass"),
    ],
    "suffix_omitted": [
        ("pieces.append((right_start, stop))", "pass"),
    ],
    "unit_suffix_omitted": [
        ("if right_start < stop:", "if right_start + 1 < stop:"),
    ],
    "unit_prefix_omitted": [
        ("if start < left_stop:", "if start + 1 < left_stop:"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "rejection_exception_is_unspecified": [
        ("raise ValueError(\"reversed span\")", "raise RuntimeError(\"invalid endpoints\")"),
    ],
    "conditional_clipping": [
        ("left_stop = min(stop, cut_start)", "left_stop = stop if stop <= cut_start else cut_start"),
        ("right_start = max(start, cut_stop)", "right_start = start if start >= cut_stop else cut_stop"),
    ],
    "equivalent_strict_length_checks": [
        ("if start < left_stop:", "if left_stop - start > 0:"),
        ("if right_start < stop:", "if stop - right_start > 0:"),
    ],
    "integer_subtypes_normalized": [
        ("    if start > stop or cut_start > cut_stop:", "    start, stop, cut_start, cut_stop = map(int, (start, stop, cut_start, cut_stop))\n    if start > stop or cut_start > cut_stop:"),
    ],
    "result_list_subclass": [
        ("    pieces = []", "    class Pieces(list):\n        pass\n    pieces = Pieces()"),
    ],
    "tuple_subclass_endpoints": [
        ("    pieces = []", "    from collections import namedtuple\n    Span = namedtuple(\"Span\", (\"start\", \"stop\"))\n    pieces = []"),
        ("pieces.append((start, left_stop))", "pieces.append(Span(start, left_stop))"),
        ("pieces.append((right_start, stop))", "pieces.append(Span(right_start, stop))"),
    ],
    "separate_order_checks": [
        ("    if start > stop or cut_start > cut_stop:\n        raise ValueError(\"reversed span\")", "    if start > stop:\n        raise ArithmeticError(\"reversed source\")\n    if cut_start > cut_stop:\n        raise LookupError(\"reversed cut\")"),
    ],
    "suffix_inserted_before_prefix": [
        ("        pieces.append((start, left_stop))", "        pieces.insert(0, (start, left_stop))"),
    ],
    "explicit_nonoverlap_fast_path": [
        ("    pieces = []", "    if cut_stop <= start or stop <= cut_start:\n        return [(start, stop)]\n    pieces = []"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
