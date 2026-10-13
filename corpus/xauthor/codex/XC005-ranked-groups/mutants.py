"""복사 경계 변이 - 주장별 약화와 격리를 유지하는 구현을 대조한다."""

COPY = "    return [list(group) for group in groups]"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "outer_only": [(COPY, "    return list(groups)")],
    "inner_only": [(COPY, "    groups[:] = [list(group) for group in groups]\n    return groups")],
    "first_row_shared": [(COPY, "    return [group if i == 0 else list(group) for i, group in enumerate(groups)]")],
    "last_row_shared": [(COPY, "    return [group if i == len(groups) - 1 else list(group) for i, group in enumerate(groups)]")],
    "empty_outer_shared": [(COPY, "    return [list(group) for group in groups] if groups else groups")],
    "singleton_outer_shared": [(COPY, "    return [list(group) for group in groups] if len(groups) != 1 else groups")],
    "large_outer_shared": [(COPY, "    return [list(group) for group in groups] if len(groups) < 257 else groups")],
    "large_inner_shared": [(COPY, "    return [list(group) if len(group) < 257 else group for group in groups]")],
    "subclass_outer_shared": [(COPY, "    return [list(group) for group in groups] if type(groups) is list else groups")],
    "subclass_inner_shared": [(COPY, "    return [list(group) if type(group) is list else group for group in groups]")],
    "bool_row_shared": [(COPY, "    return [group if any(isinstance(x, bool) for x in group) else list(group) for group in groups]")],
    "huge_score_row_shared": [(COPY, "    return [group if any(abs(x) > 10**100 for x in group) else list(group) for group in groups]")],
    "shared_input_row_reused": [(COPY, "    return [group if sum(other is group for other in groups) > 1 else list(group) for group in groups]")],
    "mutation_before_rejection": [('        raise ValueError("count must be nonnegative")', '        groups.clear()\n        raise ValueError("count must be nonnegative")')],
    "negative_returns_input": [('        raise ValueError("count must be nonnegative")', '        return groups')],
    "zero_limit_bypass": [("    groups = _copy_groups(groups)", "    groups = _copy_groups(groups) if count else groups")],
    "huge_limit_bypass": [("    groups = _copy_groups(groups)", "    groups = _copy_groups(groups) if count < 10**100 else groups")],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "slices": [(COPY, "    return [group[:] for group in groups]")],
    "copy_methods": [(COPY, "    return [group.copy() for group in groups]")],
    "empty_rows_reused_then_removed": [(COPY, "    return [list(group) if group else group for group in groups]")],
    "nested_comprehensions": [(COPY, "    return [[value for value in group] for group in groups]")],
    "deepcopy": [(COPY, "    from copy import deepcopy\n    return deepcopy(groups)")],
    "exception_type": [("raise ValueError", "raise RuntimeError")],
    "list_subclass": [(COPY, "    class Rows(list):\n        pass\n    return Rows(Rows(group) for group in groups)")],
    "copy_before_validation": [("    if count < 0:", "    groups = _copy_groups(groups)\n    if count < 0:"), ("    groups = _copy_groups(groups)\n    _rank_in_place", "    _rank_in_place")],
}

RACY: dict[str, list[tuple[str, str]]] = {}
