"""D091 변이 - 쓰는 단계 7개 · 검토 0개 (약화 6 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '표에 없으면 그대로 (twin 꼴)': [
        ('    if sort not in columns:\n        raise ValueError(f"정렬할 수 없는 열: {sort!r}")\n', ''),
        ('{columns[sort]}', '{columns.get(sort, sort)}'),
    ],
    'startswith 확인': [
        ('    if sort not in columns:\n', '    if not any(sort.startswith(key) for key in columns):\n'),
        ('{columns[sort]}', '{columns.get(sort, sort)}'),
    ],
    'strip 해서 확인 · 원문 사용': [
        ('    if sort not in columns:\n', '    if sort.strip() not in columns:\n'),
        ('{columns[sort]}', '{columns.get(sort, sort)}'),
    ],
    'lower 해서 확인 · 원문 사용': [
        ('    if sort not in columns:\n', '    if sort.lower() not in columns:\n'),
        ('{columns[sort]}', '{columns.get(sort, sort)}'),
    ],
    '거부 목록': [
        ('    if sort not in columns:\n', '    if ";" in sort or "--" in sort:\n'),
        ('{columns[sort]}', '{columns.get(sort, sort)}'),
    ],
    '쉼표로 나눠 첫 칸만 확인': [
        ('    if sort not in columns:\n', '    if sort.split(",")[0] not in columns:\n'),
        ('{columns[sort]}', "{', '.join(columns.get(k, k) for k in sort.split(','))}"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'KeyError 로 거절 (안전)': [
        ('    if sort not in columns:\n        raise ValueError(f"정렬할 수 없는 열: {sort!r}")\n', ''),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
