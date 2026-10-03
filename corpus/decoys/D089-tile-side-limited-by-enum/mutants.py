"""D089 변이 - 쓰는 단계 7개 · 검토 0개 (약화 5 · 안전 2 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    'int 변환 (twin 꼴)': [
        ('    size = Side(side)\n', '    size = int(side)\n'),
    ],
    '열거형 인스턴스만 확인': [
        ('    size = Side(side)\n', '    size = Side(side) if isinstance(side, Side) else int(side)\n'),
    ],
    '모르는 값은 그대로': [
        ('    size = Side(side)\n', '    try:\n        size = Side(side)\n    except ValueError:\n        size = int(side)\n'),
    ],
    '위로만 자르기': [
        ('    size = Side(side)\n', '    size = min(int(side), Side.LARGE)\n'),
    ],
    '열거형에 멤버 추가': [
        ('    LARGE = 64\n', '    LARGE = 64\n    XLARGE = 96\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '양쪽으로 자르기 (안전)': [
        ('    size = Side(side)\n', '    size = max(0, min(int(side), Side.LARGE))\n'),
    ],
    'int 뒤 열거형 (안전)': [
        ('    size = Side(side)\n', '    size = Side(int(side))\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
