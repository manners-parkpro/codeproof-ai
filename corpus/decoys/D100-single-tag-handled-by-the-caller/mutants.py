"""D100 변이 - 쓰는 단계 5개 · 검토 0개 (약화 4 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '문자열 분기 빠짐 (twin 꼴)': [
        ('    if isinstance(tags, str):\n        return tags\n', ''),
    ],
    'type(...) is str': [
        ('    if isinstance(tags, str):\n', '    if type(tags) is str:\n'),
    ],
    '한 글자짜리만 문자열로': [
        ('    if isinstance(tags, str):\n', '    if isinstance(tags, str) and len(tags) == 1:\n'),
    ],
    '빈 문자열은 _joined 로': [
        ('    if isinstance(tags, str):\n', '    if tags and isinstance(tags, str):\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '목록이면 잇기 (안전)': [
        ('    if isinstance(tags, str):\n        return tags\n    return _joined(tags)\n', '    if isinstance(tags, list):\n        return _joined(tags)\n    return tags\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
