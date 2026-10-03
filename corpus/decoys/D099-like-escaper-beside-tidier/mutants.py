"""D099 변이 - 쓰는 단계 6개 · 검토 0개 (약화 5 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '공백 정리만 (twin 꼴)': [
        ('    pattern = f"%{_escape_like(_tidy(term))}%"\n', '    pattern = f"%{_tidy(term)}%"\n'),
    ],
    '% 만 이스케이프': [
        ('.replace("_", "\\\\_")', ''),
    ],
    '역슬래시를 나중에': [
        ('return term.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_")', 'return term.replace("%", "\\\\%").replace("_", "\\\\_").replace("\\\\", "\\\\\\\\")'),
    ],
    'ESCAPE 절 빠짐': [
        (" ESCAPE '\\\\'", ''),
    ],
    'NUL 거절 빠짐': [
        ('    if "\\x00" in term:\n        raise ValueError("검색어에 NUL 이 들어 있다")\n', ''),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '다른 이스케이프 글자 (안전)': [
        ('return term.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_")', 'return term.replace("!", "!!").replace("%", "!%").replace("_", "!_")'),
        (" ESCAPE '\\\\'", " ESCAPE '!'"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
