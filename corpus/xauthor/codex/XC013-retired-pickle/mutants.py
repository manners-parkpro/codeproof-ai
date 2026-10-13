"""주장 축별 변이 - 형식과 페이로드의 값 및 하위 타입과 검사 뒤 상태를 각각 탐침한다."""

_GATE = 'if encoding not in ("json", "utf8"):'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "허용 집합에 폐기 형식 추가": [
        (_GATE, 'if encoding not in ("json", "utf8", "pickle"):'),
    ],
    "가드 우회": [
        (_GATE, "if False:"),
    ],
    "최적화에서 사라지는 assert": [
        (
            _GATE + '\n        raise ValueError("unsupported encoding")',
            'assert encoding in ("json", "utf8")',
        ),
    ],
    "빈 페이로드만 검사 생략": [
        (_GATE, 'if payload and encoding not in ("json", "utf8"):'),
    ],
    "64KiB 이상만 검사 생략": [
        (_GATE, 'if len(payload) < 65536 and encoding not in ("json", "utf8"):'),
    ],
    "str 하위 타입만 검사 생략": [
        (_GATE, 'if type(encoding) is str and encoding not in ("json", "utf8"):'),
    ],
    "표준 Enum 혼합형만 검사 생략": [
        (_GATE, 'if not hasattr(encoding, "value") and encoding not in ("json", "utf8"):'),
    ],
    "bytes 하위 타입만 검사 생략": [
        (_GATE, 'if type(payload) is bytes and encoding not in ("json", "utf8"):'),
    ],
    "프로토콜 5만 검사 생략": [
        (_GATE, 'if not payload.startswith(b"\\x80\\x05") and encoding not in ("json", "utf8"):'),
    ],
    "허용된 JSON 이름을 검사 뒤 변경": [
        (
            '    if encoding == "pickle":',
            '    encoding = "pickle" if encoding == "json" else encoding\n    if encoding == "pickle":',
        ),
    ],
    "UTF8 이름도 폐기 분기에 진입": [
        ('if encoding == "pickle":', 'if encoding in ("pickle", "utf8"):'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "거절 예외 변경": [
        ('raise ValueError("unsupported encoding")', 'raise TypeError("unsupported encoding")'),
    ],
    "거절은 조기 반환": [
        ('raise ValueError("unsupported encoding")', "return None"),
    ],
    "허용 집합을 list로 표현": [
        (_GATE, 'if encoding not in ["json", "utf8"]:'),
    ],
    "허용 집합을 set으로 표현": [
        (_GATE, 'if encoding not in {"json", "utf8"}:'),
    ],
    "허용 집합을 frozenset으로 표현": [
        (_GATE, 'if encoding not in frozenset(("json", "utf8")):'),
    ],
    "논리곱으로 같은 가드 표현": [
        (_GATE, 'if encoding != "json" and encoding != "utf8":'),
    ],
    "직접 import한 sink": [
        ("import pickle", "from pickle import loads"),
        ("pickle.loads(payload)", "loads(payload)"),
    ],
    "허용 형식을 UTF8로 축소": [
        (_GATE, 'if encoding != "utf8":'),
    ],
    "도달 불가능한 분기 삭제": [
        ('    if encoding == "pickle":\n        return pickle.loads(payload)\n', ""),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
