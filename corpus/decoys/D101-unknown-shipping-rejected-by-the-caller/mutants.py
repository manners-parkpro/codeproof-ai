"""D101 변이 - 쓰는 단계 6개 · 검토 0개 (약화 5 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '방식 확인 빠짐 (twin 꼴)': [
        ('    if kind not in _KINDS:\n        raise ValueError(f"모르는 배송 방식: {kind!r}")\n', ''),
    ],
    'lower 해서 확인 · 원문 전달': [
        ('    if kind not in _KINDS:\n', '    if kind.lower() not in _KINDS:\n'),
    ],
    'strip 해서 확인 · 원문 전달': [
        ('    if kind not in _KINDS:\n', '    if kind.strip() not in _KINDS:\n'),
    ],
    'startswith 확인': [
        ('    if kind not in _KINDS:\n', '    if not kind.startswith(_KINDS):\n'),
    ],
    'NFKC 로 확인 · 원문 전달': [
        ('import math\n', 'import math\nimport unicodedata\n'),
        ('    if kind not in _KINDS:\n', '    if unicodedata.normalize("NFKC", kind) not in _KINDS:\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '정규화해서 확인하고 전달 (안전)': [
        ('    if kind not in _KINDS:\n', '    kind = kind.strip().lower()\n    if kind not in _KINDS:\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
