"""D124 변이 - 쓰는 단계 10개 · 쓰는 단계 점검 10개 · 독립 검토 5개 (약화 16 · 안전 9 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_PORTS = "_PORTS = range(1024, 49152)\n"
_HEAD = '"""허용 포트 - 모듈이 쥔 포트 모음은 range 라서 그대로 돌려줘도 받은 쪽이 고칠 수 없다."""\n'
_CONTAINS = "    return port in _PORTS\n"


def _span(frozen: bool) -> list[tuple[str, str]]:
    """포트 구간을 dataclass 로 쥐는 변이 - 공개 속성 low · high 를 가진다."""
    deco = "@dataclass(frozen=True)" if frozen else "@dataclass"
    return [
        (_HEAD, _HEAD + "\nfrom dataclasses import dataclass\n"),
        (_PORTS, f"{deco}\nclass _Span:\n    low: int\n    high: int\n\n"
                 "    def __iter__(self):  # type: ignore[no-untyped-def]\n        return iter(range(self.low, self.high + 1))\n\n"
                 "    def __contains__(self, port: object) -> bool:\n        return isinstance(port, int) and self.low <= port <= self.high\n\n\n"
                 "_PORTS = _Span(1024, 49151)  # type: ignore[assignment]\n"),
    ]

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[불변] list 로 쥠 (twin)": [(_PORTS, "_PORTS = list(range(1024, 49152))\n")],
    "[불변] set 으로 쥠": [(_PORTS, "_PORTS = set(range(1024, 49152))  # type: ignore[assignment]\n")],
    "[불변] array 로 쥠": [
        (_HEAD, _HEAD + "\nimport array\n"),
        (_PORTS, '_PORTS = array.array("H", range(1024, 49152))\n'),
    ],
    "[불변] deque 로 쥠": [
        (_HEAD, _HEAD + "\nimport collections\n"),
        (_PORTS, "_PORTS = collections.deque(range(1024, 49152))\n"),
    ],
    "[경계] 끝 포트 49151 을 뺌": [(_PORTS, "_PORTS = range(1024, 49151)\n")],
    "[경계] 1023 까지 넣음": [(_PORTS, "_PORTS = range(1023, 49152)\n")],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[경계] is_allowed 만 1023 도 허용": [(_CONTAINS, "    return 1023 <= port <= 49151\n")],
    "[수 · 형] is_allowed 가 정확히 int 인 것만 받음": [(_CONTAINS, "    return type(port) is int and port in _PORTS\n")],
    "[불변] allowed_ports 가 is_allowed 와 다른 list 를 돌려줌": [
        (_PORTS, "_PORTS = range(1024, 49152)\n_LISTED = list(_PORTS)\n"),
        ("    return _PORTS\n", "    return _LISTED\n"),
    ],
    "[불변] memoryview 로 쥠": [
        (_HEAD, _HEAD + "\nimport array\n"),
        (_PORTS, '_PORTS = memoryview(array.array("H", range(1024, 49152)))  # type: ignore[assignment]\n'),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[공개 속성] frozen 아닌 dataclass 로 쥠": _span(frozen=False),
    "[한 단계 아래] 읽기 전용 memoryview 로 쥠 - .obj 와 release 로 바뀜": [
        (_HEAD, _HEAD + "\nimport array\n"),
        (_PORTS, '_PORTS = memoryview(array.array("H", range(1024, 49152))).toreadonly()  # type: ignore[assignment]\n'),
    ],
    # 독립 검토 - is_allowed 를 고정 탐침으로만 봐서 구간 안의 구멍이 지나갔다 (§3.5 표 「고정 탐침 대신 구간 전체」)
    "[구간 전체] is_allowed 가 DB 포트 몇 개를 막음": [("    return port in _PORTS\n", "    return port in _PORTS and port not in {3306, 5432, 6379, 27017}\n")],
    "[구간 전체] is_allowed 가 32768 에서 한 칸 빠짐": [("    return port in _PORTS\n", "    return 1024 <= port < 32768 or 32768 < port <= 49151\n")],
    "[불변] UserList 로 쥠": [(_HEAD, _HEAD + "\nimport collections\n"), (_PORTS, "_PORTS = collections.UserList(range(1024, 49152))\n")],
    "[불변] dict.fromkeys 로 쥠": [(_PORTS, "_PORTS = dict.fromkeys(range(1024, 49152))  # type: ignore[assignment]\n")],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "tuple 로 쥠 (안전)": [(_PORTS, "_PORTS = tuple(range(1024, 49152))\n")],
    "frozenset 으로 쥠 (안전)": [(_PORTS, "_PORTS = frozenset(range(1024, 49152))  # type: ignore[assignment]\n")],
    "list 로 쥐고 tuple 사본을 돌려줌 (안전)": [
        (_PORTS, "_PORTS = list(range(1024, 49152))\n"),
        ("    return _PORTS\n", "    return tuple(_PORTS)\n"),
    ],
    "is_allowed 를 비교식으로 (안전)": [("    return port in _PORTS\n", "    return 1024 <= port <= 49151\n")],
    "매번 새 list 사본을 돌려줌 (안전)": [("    return _PORTS\n", "    return list(_PORTS)\n")],
    "is_allowed 를 range 의 start · stop 비교로 (안전)": [(_CONTAINS, "    return _PORTS.start <= port < _PORTS.stop\n")],
    "dict 의 keys 뷰로 쥠 (안전)": [(_PORTS, "_PORTS = dict.fromkeys(range(1024, 49152)).keys()  # type: ignore[assignment]\n")],
    "frozen dataclass 로 쥠 (안전 - __init__ 재호출은 주장 밖)": _span(frozen=True),
    "MappingProxyType 로 쥠 (안전)": [
        (_HEAD, _HEAD + "\nimport types\n"),
        (_PORTS, "_PORTS = types.MappingProxyType(dict.fromkeys(range(1024, 49152)))  # type: ignore[assignment]\n"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
