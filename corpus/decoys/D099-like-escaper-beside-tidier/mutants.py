"""D099 변이 - 쓰는 단계 6개 · 검토 0개 · 교차 3개 (약화 7 · 안전 2 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_REJECT = (
    '    if any(ch in term for ch in "\\x00\\ufffd\\ufffe\\uffff"):\n'
    '        raise ValueError("검색어에 NUL 이나 SQLite 가 U+FFFD 로 읽는 글자가 들어 있다")\n'
)

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
        (_REJECT, ''),
    ],
    # 교차 패밀리 감사 - SQLite 의 LIKE 는 UTF-8 을 읽을 때 U+FFFE · U+FFFF 를 U+FFFD 로 바꿔 견준다
    "[U+FFFD 류] NUL 만 거절 (감사 전 decoy)": [(_REJECT, '    if "\\x00" in term:\n        raise ValueError("검색어에 NUL 이 들어 있다")\n')],
    "[U+FFFD 류] U+FFFE · U+FFFF 만 거절 - 검색어의 U+FFFD 가 그 둘이 든 이름을 찾는다": [
        (_REJECT, _REJECT.replace("\\ufffd", "")),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '다른 이스케이프 글자 (안전)': [
        ('return term.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_")', 'return term.replace("!", "!!").replace("%", "!%").replace("_", "!_")'),
        (" ESCAPE '\\\\'", " ESCAPE '!'"),
    ],
    "[U+FFFD 류] 정규식 문자 클래스로 거절 (안전)": [
        ("import sqlite3\n", "import re\nimport sqlite3\n"),
        (_REJECT.split("\n")[0] + "\n", '    if re.search(r"[\\x00\\ufffd-\\uffff]", term):\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
