"""D030 변이 - 독립 검토 10개 (약화 6 · 안전 4 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] band size abs': [('    return max(0, high - low + 1)\n', '    return abs(high - low) + 1\n')],
    '[독립 검토] band size max inside': [('    return max(0, high - low + 1)\n', '    return max(0, high - low) + 1\n')],
    '[독립 검토] band size prefix': [('    return max(0, high - low + 1)\n', '    return high - low + 1\n')],
    '[독립 검토] grade high plus 1': [('        if low <= score <= high:\n', '        if low <= score <= high + 1:\n')],
    '[독립 검토] grade low minus 1': [('        if low <= score <= high:\n', '        if low - 1 <= score <= high:\n')],
    '[독립 검토] grade upper open': [('        if low <= score <= high:\n', '        if low <= score < high:\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] grade lt high plus 1': [('        if low <= score <= high:\n', '        if low <= score < high + 1:\n')],
    '[독립 검토] grade reversed scan': [('    for low, high, label in _BANDS:\n', '    for low, high, label in reversed(_BANDS):\n')],
    '[독립 검토] len range': [('    return max(0, high - low + 1)\n', '    return len(range(low, high + 1))\n')],
    '[독립 검토] out of range LookupError': [('    raise ValueError(score)\n', '    raise LookupError(score)\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
