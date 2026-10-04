"""D047 변이 - 독립 검토 · 고치기 전 판 9개 (약화 5 · 안전 4 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] 지수 상한 1024': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    return min(2.0 ** min(max(attempt, 0), 1024), _MAX_DELAY)\n')],
    '[독립 검토] 지수 상한 2000': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    return min(2.0 ** min(max(attempt, 0), 2000), _MAX_DELAY)\n')],
    '[독립 검토] 지수 상한 없음': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    return min(2.0 ** max(attempt, 0), _MAX_DELAY)\n')],
    '[독립 검토] type(attempt) is int 일 때만 묶음': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    return min(2.0 ** (min(max(attempt, 0), 64) if type(attempt) is int else attempt), _MAX_DELAY)\n')],
    '[고치기 전 판] 음수 쪽을 묶지 않음': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    return min(2.0 ** min(attempt, 64), _MAX_DELAY)\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] 지수 상한 1023': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    return min(2.0 ** min(max(attempt, 0), 1023), _MAX_DELAY)\n')],
    '[독립 검토] OverflowError 를 잡아 상한': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    try:\n        return min(2.0 ** max(attempt, 0), _MAX_DELAY)\n    except OverflowError:\n        return _MAX_DELAY\n')],
    '[독립 검토] attempt >= 5 면 바로 상한': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    if attempt >= 5:\n        return _MAX_DELAY\n    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n')],
    '[쓰는 단계] 음수를 조건으로 0 에 맞춤': [('    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)\n', '    if attempt < 0:\n        attempt = 0\n    return min(2.0 ** min(attempt, 64), _MAX_DELAY)\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
