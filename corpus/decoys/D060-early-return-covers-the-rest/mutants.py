"""D060 변이 - 독립 검토 10개 (약화 7 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] 음수에서 1 / 0 을 실행하고 ValueError 로 바꿔 올림': [('    if amount < 100:\n        return 0.0\n    return 1 / 0\n', '    if 0 <= amount < 100:\n        return 0.0\n    try:\n        return 1 / 0\n    except ZeroDivisionError:\n        raise ValueError(amount) from None\n')],
    '[독립 검토] 0 to 100': [('    if amount < 100:\n', '    if 0 <= amount < 100:\n')],
    '[독립 검토] ge -(2**63)': [('    if amount < 100:\n', '    if -(2**63) <= amount < 100:\n')],
    '[독립 검토] ge -100': [('    if amount < 100:\n', '    if amount >= -100:\n')],
    '[독립 검토] lt 99': [('    if amount < 100:\n', '    if amount < 99:\n')],
    '[독립 검토] prefix ge 0': [('    if amount < 100:\n', '    if amount >= 0:\n')],
    '[독립 검토] type is int': [('    if amount < 100:\n', '    if type(amount) is int and amount < 100:\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] 음수를 ValueError 로 먼저 거절': [('    if amount < 100:\n', '    if amount < 0:\n        raise ValueError(amount)\n    if amount < 100:\n')],
    '[독립 검토] else return': [('    if amount < 100:\n        return 0.0\n    return 1 / 0\n', '    return 0.0\n')],
    '[독립 검토] le 99': [('    if amount < 100:\n', '    if amount <= 99:\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
