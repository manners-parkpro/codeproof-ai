"""D107 변이 - 쓰는 단계 8개 · 검토 0개 (약화 5 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[둘 다] 복사 없이 (twin)': [
        ('        self.headers = dict(headers)\n', '        self.headers = headers\n'),
    ],
    '[기본값 경로] 기본값일 때만 그대로': [
        ('        self.headers = dict(headers)\n', '        self.headers = headers if headers is _DEFAULT_HEADERS else dict(headers)\n'),
    ],
    '[호출자 경로] 기본값일 때만 복사': [
        ('        self.headers = dict(headers)\n', '        self.headers = dict(headers) if headers is _DEFAULT_HEADERS else headers\n'),
    ],
    '[dict 의 종류] 정확히 dict 일 때만 복사': [
        ('        self.headers = dict(headers)\n', '        self.headers = dict(headers) if type(headers) is dict else headers\n'),
    ],
    '[dict 의 종류] dict 가 아닐 때만 복사': [
        ('        self.headers = dict(headers)\n', '        self.headers = headers if isinstance(headers, dict) else dict(headers)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'copy() (안전)': [
        ('        self.headers = dict(headers)\n', '        self.headers = headers.copy()\n'),
    ],
    '펼쳐 새 dict (안전)': [
        ('        self.headers = dict(headers)\n', '        self.headers = {**headers}\n'),
    ],
    '지우고 붙일 때 새 dict 로 바꿔 끼움 (안전)': [
        ('        self.headers = dict(headers)\n', '        self.headers = headers\n'),
        ('    for name in [name for name in request.headers if name.lower() == "authorization"]:\n        del request.headers[name]\n    request.headers |= {"Authorization": f"Bearer {token}"}\n', '    kept = {name: value for name, value in request.headers.items() if name.lower() != "authorization"}\n    request.headers = kept | {"Authorization": f"Bearer {token}"}\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
