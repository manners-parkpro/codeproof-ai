"""D133 변이 - 쓰는 단계 14개 · 쓰는 단계 점검 23개 · 독립 검토 7개 (약화 33 · 안전 11 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_CHECK = '    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n'
_FIND = "    return re.findall(patterns[kind], text)\n"
_ORDER = '        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n'
_PHONE = '        "phone": r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])",\n'
_POST = '        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[거절] 표에 없으면 kind 를 정규식으로 (twin)": [(_CHECK + _FIND, "    return re.findall(patterns.get(kind, kind), text)\n")],
    "[거절] 표에 없으면 빈 목록": [(_CHECK, "    if kind not in patterns:\n        return []\n")],
    "[거절] 대소문자를 접어 고름": [
        (_CHECK + _FIND, "    kind = kind.lower()\n" + _CHECK + _FIND),
    ],
    "[거절] 앞뒤 공백을 떼고 고름": [(_CHECK + _FIND, "    kind = kind.strip()\n" + _CHECK + _FIND)],
    "[경계] 우편번호 앞뒤 확인 없음": [(_POST, '        "postcode": r"[0-9]{5}",\n')],
    "[경계] 주문번호 앞 영문 확인 없음": [(_ORDER, '        "order": r"ORD-[0-9]{8}(?![0-9])",\n')],
    "[숫자] \\d - ASCII 아닌 숫자도": [(_POST, '        "postcode": r"(?<!\\d)\\d{5}(?!\\d)",\n')],
    "[대소문자] 주문번호를 IGNORECASE 로": [(_ORDER, '        "order": r"(?i)(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n')],
    "[개수] 전화번호 가운데 3~4자리": [(_PHONE, '        "phone": r"(?<![0-9])010-[0-9]{3,4}-[0-9]{4}(?![0-9])",\n')],
    "[차례] 겹친 값을 하나로 · 정렬": [(_FIND, "    return sorted(set(re.findall(patterns[kind], text)))\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[거절] 종류를 NFKC 로 바꿔 고름 - 전각 ｐｈｏｎｅ 을 받음': [('    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n    return re.findall(patterns[kind], text)\n', '    kind = unicodedata.normalize("NFKC", kind)\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n    return re.findall(patterns[kind], text)\n'), ('import re\n', 'import re\nimport unicodedata\n')],
    '[하위 타입] str(kind) 로 고름 - (str, Enum) 혼합형을 거절': [('    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n    return re.findall(patterns[kind], text)\n', '    kind = str(kind)\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n    return re.findall(patterns[kind], text)\n')],
    '[숫자] 전화번호 가운데 · 끝 \\d{4} - ASCII 아닌 숫자도': [('        "phone": r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])",\n', '        "phone": r"(?<![0-9])010-\\d{4}-\\d{4}(?![0-9])",\n')],
    '[숫자] 우편번호 앞뒤 확인을 \\d 로 - 옆의 ASCII 아닌 숫자가 막음': [('        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n', '        "postcode": r"(?<!\\d)[0-9]{5}(?!\\d)",\n')],
    '[숫자] 전화번호 앞뒤 확인을 \\d 로': [('        "phone": r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])",\n', '        "phone": r"(?<!\\d)010-[0-9]{4}-[0-9]{4}(?!\\d)",\n')],
    '[숫자] 주문번호 뒤 확인을 \\d 로': [('        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n', '        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?!\\d)",\n')],
    '[구간 끝] 전화번호 숫자 [0-8] - 9 를 뺌': [('        "phone": r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])",\n', '        "phone": r"(?<![0-9])010-[0-8]{4}-[0-8]{4}(?![0-9])",\n')],
    '[구간 끝] 주문번호 숫자 [0-8] - 9 를 뺌': [('        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n', '        "order": r"(?<![A-Za-z0-9])ORD-[0-8]{8}(?![0-9])",\n')],
    '[구간 끝] 우편번호 뒤 확인 [1-9] - 뒤의 0 을 놓침': [('        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n', '        "postcode": r"(?<![0-9])[0-9]{5}(?![1-9])",\n')],
    '[구간 끝] 우편번호 앞 확인 [1-9] - 앞의 0 을 놓침': [('        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n', '        "postcode": r"(?<![1-9])[0-9]{5}(?![0-9])",\n')],
    '[구간 끝] 주문번호 앞 확인 [A-Za-z1-9] - 앞의 0 을 놓침': [('        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n', '        "order": r"(?<![A-Za-z1-9])ORD-[0-9]{8}(?![0-9])",\n')],
    '[구간 끝] 주문번호 앞 확인에 _ 를 더함 - _ORD- 를 버림': [('        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n', '        "order": r"(?<![A-Za-z0-9_])ORD-[0-9]{8}(?![0-9])",\n')],
    '[거절] 표에 종류 하나를 더함 (zip)': [('        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n', '        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n        "zip": r"(?<![0-9])[0-9]{5}(?![0-9])",\n')],
    '[하위 타입] type(text) is str 만 받음 - str 하위 클래스 글을 거절': [('    return re.findall(patterns[kind], text)\n', '    if type(text) is not str:\n        raise TypeError(type(text))\n    return re.findall(patterns[kind], text)\n')],
    '[패턴] 종류 이름도 패턴에 섞음 (patterns[kind] | kind)': [('    return re.findall(patterns[kind], text)\n', '    return re.findall(patterns[kind] + "|" + kind, text)\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[하위 타입] type(kind) is str 만 받음': [('    if kind not in patterns:\n', '    if type(kind) is not str or kind not in patterns:\n')],
    '[거절] 정규식 꼴의 kind 는 그대로 패턴으로': [('    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n', '    if set(kind) & set(".*+?[](){}|^$"):\n        return re.findall(kind, text)\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n')],
    '[거절] 빈 kind 는 빈 목록': [('    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n', '    if not kind:\n        return []\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    "[구분자] 전화번호의 '-' 를 [-. ] 로 넓힘 - 010.1234.5678 · 010 1234 5678 도 맞음": [('"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])"', '"(?<![0-9])010[-. ][0-9]{4}[-. ][0-9]{4}(?![0-9])"')],
    "[구분자] 주문번호의 '-' 를 [- ] 로 넓힘 - ORD 12345678 도 맞음": [('"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])"', '"(?<![A-Za-z0-9])ORD[- ][0-9]{8}(?![0-9])"')],
    '[거절] 세 글자 이상의 고유 접두사를 받아 줌 (allow_abbrev 꼴 - post · pho · ord)': [('    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n', '    if kind not in patterns:\n        hits = [name for name in patterns if len(kind) >= 3 and name.startswith(kind)]\n        if len(hits) != 1:\n            raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n        kind = hits[0]\n')],
    '[거절] 끝의 s 를 떼어 복수형을 받아 줌 (orders · phones)': [('    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n', '    kind = kind[:-1] if kind.endswith("s") and kind[:-1] in patterns else kind\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n')],
    '[거절] _ · - 를 지우고 고름 (post_code · pho-ne)': [('    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n', '    kind = kind.replace("_", "").replace("-", "")\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "compile 뒤 findall (안전)": [(_FIND, "    return re.compile(patterns[kind]).findall(text)\n")],
    "finditer 로 모음 (안전)": [(_FIND, "    return [m.group() for m in re.finditer(patterns[kind], text)]\n")],
    "확인 대신 첨자의 KeyError 로 거절 (안전)": [(_CHECK + _FIND, "    pattern = patterns[kind]\n    return re.findall(pattern, text)\n")],
    "거절을 LookupError 로 (안전)": [(_CHECK, '    if kind not in patterns:\n        raise LookupError(kind)\n')],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    're.ASCII 플래그를 더함 (안전)': [('    return re.findall(patterns[kind], text)\n', '    return re.findall(patterns[kind], text, re.ASCII)\n')],
    '우편번호를 (?a) 와 \\d 로 - 같은 패턴 (안전)': [('        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n', '        "postcode": r"(?a)(?<!\\d)\\d{5}(?!\\d)",\n')],
    'match 문으로 고름 · 거절은 KeyError (안전)': [('    patterns = {\n        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n        "phone": r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])",\n        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n    }\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n    return re.findall(patterns[kind], text)\n', '    match kind:\n        case "order":\n            pattern = r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])"\n        case "phone":\n            pattern = r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])"\n        case "postcode":\n            pattern = r"(?<![0-9])[0-9]{5}(?![0-9])"\n        case _:\n            raise KeyError(kind)\n    return re.findall(pattern, text)\n')],
    'from re import findall - import 꼴 (안전)': [('import re\n', 'from re import findall\n'), ('    return re.findall(patterns[kind], text)\n', '    return findall(patterns[kind], text)\n')],
    '표를 (종류, 패턴) 튜플로 · 차례로 견줌 - 컨테이너 (안전)': [('    patterns = {\n        "order": r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])",\n        "phone": r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])",\n        "postcode": r"(?<![0-9])[0-9]{5}(?![0-9])",\n    }\n    if kind not in patterns:\n        raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n    return re.findall(patterns[kind], text)\n', '    patterns = (\n        ("order", r"(?<![A-Za-z0-9])ORD-[0-9]{8}(?![0-9])"),\n        ("phone", r"(?<![0-9])010-[0-9]{4}-[0-9]{4}(?![0-9])"),\n        ("postcode", r"(?<![0-9])[0-9]{5}(?![0-9])"),\n    )\n    for name, pattern in patterns:\n        if kind == name:\n            return re.findall(pattern, text)\n    raise ValueError(f"찾을 수 없는 종류: {kind!r}")\n')],
    # 독립 검토 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '튜플로 돌려줌 (안전 - 주장이 정하지 않은 컨테이너)': [('    return re.findall(patterns[kind], text)\n', '    return tuple(re.findall(patterns[kind], text))\n')],
    'finditer 의 생성기로 돌려줌 (안전 - 같은 조각 · 같은 차례)': [('    return re.findall(patterns[kind], text)\n', '    return (m.group() for m in re.finditer(patterns[kind], text))\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
