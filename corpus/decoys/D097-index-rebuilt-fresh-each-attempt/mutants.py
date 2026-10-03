"""D097 변이 - 쓰는 단계 4개 · 검토 0개 (약화 3 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '색인을 한 번만 만듦 (twin 꼴)': [
        ('    for attempt in range(attempts):\n        index: dict[str, list[str]] = {}\n', '    index: dict[str, list[str]] = {}\n    for attempt in range(attempts):\n'),
    ],
    '끊기면 조각을 돌려줌': [
        ('            if attempt == attempts - 1:\n                raise\n            continue\n', '            return index\n'),
    ],
    '재설정 대신 중복만 막음': [
        ('    for attempt in range(attempts):\n        index: dict[str, list[str]] = {}\n', '    index: dict[str, list[str]] = {}\n    for attempt in range(attempts):\n'),
        ('                    index.setdefault(word, []).append(doc_id)\n', '                    ids = index.setdefault(word, [])\n                    if doc_id not in ids:\n                        ids.append(doc_id)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '한 번 만들고 시도마다 비움 (안전)': [
        ('    for attempt in range(attempts):\n        index: dict[str, list[str]] = {}\n', '    index: dict[str, list[str]] = {}\n    for attempt in range(attempts):\n        index.clear()\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
