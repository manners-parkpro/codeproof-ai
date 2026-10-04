"""D119 변이 - 쓰는 단계 10개 · 쓰는 단계 점검 14개 · 독립 검토 5개 (약화 18 · 안전 11 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_PICK = "    method = _METHODS[fmt]\n"
_TABLE = '_METHODS = {"csv": "to_csv", "json": "to_json"}\n'
_CALL = "    return _render(exporter, method, rows)\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[표 밖 이름] 그대로 넘김 (twin)": [
        ("    method = _METHODS[fmt]\n", "    method = _METHODS.get(fmt, fmt)\n"),
    ],
    "[표 밖 이름] to_ 를 붙여 만듦": [
        ("    method = _METHODS[fmt]\n", '    method = _METHODS.get(fmt) or f"to_{fmt}"\n'),
    ],
    "[표 밖 이름] to_ 로 시작하면 그대로": [
        ("    method = _METHODS[fmt]\n", '    method = fmt if fmt.startswith("to_") else _METHODS[fmt]\n'),
    ],
    "[표의 값 전부] 표에 다른 메서드를 더함": [
        ('_METHODS = {"csv": "to_csv", "json": "to_json"}\n', '_METHODS = {"csv": "to_csv", "json": "to_json", "raw": "dump_all"}\n'),
    ],
    "[짝] 표의 값이 뒤바뀜": [
        ('_METHODS = {"csv": "to_csv", "json": "to_json"}\n', '_METHODS = {"csv": "to_json", "json": "to_csv"}\n'),
    ],
    "[한 번] 메서드를 두 번 부름": [
        ("    return getattr(exporter, method)(rows)\n", "    getattr(exporter, method)(rows)\n    return getattr(exporter, method)(rows)\n"),
    ],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[표 밖 이름 · exporter 종류] 클래스에 있는 이름이면 그대로 부름": [
        (_PICK, "    method = fmt if hasattr(type(exporter), fmt) else _METHODS[fmt]\n"),
    ],
    "[한 번] 별칭 fmt 는 메서드를 두 번 부름": [
        (_TABLE, '_METHODS = {"csv": "to_csv", "json": "to_json", "tsv": "to_csv"}\n'),
        (_CALL, '    if fmt == "tsv":\n        _render(exporter, method, rows)\n    return _render(exporter, method, rows)\n'),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[부르는 꼴] 표에 없는 이름을 인자 없이 부름": [
        (_PICK, "    if fmt not in _METHODS:\n        getattr(exporter, fmt)()\n    method = _METHODS[fmt]\n"),
    ],
    "[형] 정확히 str 이 아니면 표를 건너뜀": [(_PICK, "    method = _METHODS[fmt] if type(fmt) is str else fmt\n")],
    "[표의 모양] 짝 튜플 표에 다른 메서드를 더함": [
        (_TABLE, '_METHODS = (("csv", "to_csv"), ("json", "to_json"), ("raw", "purge"))\n'),
        (_PICK, "    method = dict(_METHODS)[fmt]\n"),
    ],
    "[한 번] 표에 없으면 csv 와 json 을 둘 다 만들어 이어 붙임": [
        (_PICK, '    method = _METHODS.get(fmt)\n    if method is None:\n        return _render(exporter, "to_csv", rows) + _render(exporter, "to_json", rows)\n'),
    ],
    "[하나만] 표의 fmt 를 다른 형식으로 먼저 한 번 검증": [
        (_CALL, '    _render(exporter, "to_json" if method == "to_csv" else "to_csv", rows)\n    return _render(exporter, method, rows)\n'),
    ],
    # 독립 검토 - fmt 후보를 소스의 문자열 상수에서만 모아, 리터럴이 아닌 키로 만든 표를 덮지 못했다
    "[표 밖 키] StrEnum auto() 키로 표에 RAW 를 더함": [
        ("from typing import Protocol\n", "import enum\nfrom typing import Protocol\n"),
        ('_METHODS = {"csv": "to_csv", "json": "to_json"}\n',
         "class _Fmt(enum.StrEnum):\n    CSV = enum.auto()\n    JSON = enum.auto()\n    RAW = enum.auto()\n\n\n"
         '_METHODS = {_Fmt.CSV: "to_csv", _Fmt.JSON: "to_json", _Fmt.RAW: "dump_all"}\n'),
    ],
    "[표 밖 키] 메서드 이름에서 만든 키에 to_excel 을 더함": [
        ('_METHODS = {"csv": "to_csv", "json": "to_json"}\n',
         '_METHODS = {name.removeprefix("to_"): name for name in ("to_csv", "to_json", "to_excel")}\n'),
    ],
    "[표 밖 키] 대문자를 접은 키로 표에 RAW 를 더함": [
        ('_METHODS = {"csv": "to_csv", "json": "to_json"}\n',
         '_METHODS = {k.lower(): v for k, v in {"CSV": "to_csv", "JSON": "to_json", "RAW": "dump_all"}.items()}\n'),
    ],
    "[표 밖 이름] 식별자이고 _ 로 시작하지 않으면 그대로": [
        ("    method = _METHODS[fmt]\n",
         '    method = _METHODS.get(fmt) or (fmt if fmt.isidentifier() and not fmt.startswith("_") else "to_csv")\n'),
    ],
    "[표 밖 이름] getattr 기본값으로 to_csv": [
        ("    method = _METHODS[fmt]\n", "    method = _METHODS.get(fmt, fmt)\n"),
        ("    return getattr(exporter, method)(rows)\n", '    return getattr(exporter, method, getattr(exporter, "to_csv"))(rows)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "대소문자를 접어 찾음 (안전)": [
        ("    method = _METHODS[fmt]\n", "    method = _METHODS[fmt.lower()]\n"),
    ],
    "표에 없으면 ValueError (안전)": [
        ("    method = _METHODS[fmt]\n", "    method = _METHODS.get(fmt)\n    if method is None:\n        raise ValueError(fmt)\n"),
    ],
    "표에 없으면 csv 로 (안전)": [
        ("    method = _METHODS[fmt]\n", '    method = _METHODS.get(fmt, "to_csv")\n'),
    ],
    "methodcaller 로 부름 (안전)": [
        ("from typing import Protocol\n", "import operator\nfrom typing import Protocol\n"),
        ("    return getattr(exporter, method)(rows)\n", "    return operator.methodcaller(method, rows)(exporter)\n"),
    ],
    "표를 읽기 전용 매핑으로 (안전)": [
        ("from typing import Protocol\n", "from types import MappingProxyType\nfrom typing import Protocol\n"),
        (_TABLE, '_METHODS = MappingProxyType({"csv": "to_csv", "json": "to_json"})\n'),
    ],
    "NFKC 로 정규화해 찾음 (안전)": [
        ("from typing import Protocol\n", "import unicodedata\nfrom typing import Protocol\n"),
        (_PICK, '    method = _METHODS[unicodedata.normalize("NFKC", fmt)]\n'),
    ],
    "표에 별칭 tsv 를 더함 (안전)": [(_TABLE, '_METHODS = {"csv": "to_csv", "json": "to_json", "tsv": "to_csv"}\n')],
    "표에 없으면 부르지 않고 빈 문자열 (안전)": [
        (_PICK, '    method = _METHODS.get(fmt)\n    if method is None:\n        return ""\n'),
    ],
    "표를 짝 튜플로 두고 dict 로 찾음 (안전)": [
        (_TABLE, '_METHODS = (("csv", "to_csv"), ("json", "to_json"))\n'),
        (_PICK, "    method = dict(_METHODS)[fmt]\n"),
    ],
    "표 이름을 _FORMATS 로 바꿈 (안전)": [
        (_TABLE, '_FORMATS = {"csv": "to_csv", "json": "to_json"}\n'),
        (_PICK, "    method = _FORMATS[fmt]\n"),
    ],
    "match 문으로 고르고 표를 없앰 (안전)": [
        (_TABLE, ""),
        (_PICK, '    match fmt:\n        case "csv":\n            method = "to_csv"\n        case "json":\n            method = "to_json"\n'
                '        case _:\n            raise ValueError(fmt)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
