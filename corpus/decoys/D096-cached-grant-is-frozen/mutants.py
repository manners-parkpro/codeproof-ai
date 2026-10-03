"""D096 변이 - 쓰는 단계 6개 · 검토 0개 (약화 4 · 안전 2 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    'frozen 빠짐 · set (twin 꼴)': [
        ('@dataclass(frozen=True)\n', '@dataclass\n'),
        ('    roles: frozenset[str]\n', '    roles: set[str]\n'),
        ('    return Grant(frozenset(', '    return Grant(set('),
    ],
    'frozen 만 빠짐': [
        ('@dataclass(frozen=True)\n', '@dataclass\n'),
    ],
    'set 만 바뀜': [
        ('    roles: frozenset[str]\n', '    roles: set[str]\n'),
        ('    return Grant(frozenset(', '    return Grant(set('),
    ],
    'frozen 은 두고 list': [
        ('    roles: frozenset[str]\n', '    roles: list[str]\n'),
        ('    return Grant(frozenset(', '    return Grant(sorted('),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '튜플로 (안전)': [
        ('    roles: frozenset[str]\n', '    roles: tuple[str, ...]\n'),
        ('    return Grant(frozenset(', '    return Grant(tuple('),
    ],
    'slots 추가 (안전)': [
        ('@dataclass(frozen=True)\n', '@dataclass(frozen=True, slots=True)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
