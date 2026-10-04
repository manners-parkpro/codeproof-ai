"""D127 변이 - 쓰는 단계 12개 · 쓰는 단계 점검 19개 · 독립 검토 7개 (약화 27 · 안전 11 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_TABLE = '_SPECIAL = {"\\\\": r"\\5c", "*": r"\\2a", "(": r"\\28", ")": r"\\29", "\\x00": r"\\00"}\n'
_ESCAPE = "    return \"\".join(_SPECIAL.get(ch, ch) for ch in value)\n"
_CHECK = "    if len(uid.encode(\"utf-8\")) > _MAX_BYTES:\n"
_HEAD = '"""LDAP 사용자 필터 - 이웃한 두 함수 중 하나만 RFC 4515 의 특수 문자를 이스케이프한다."""\n'
_TIDY = '    return " ".join(value.split())\n'
_RETURN = '    return f"(&(objectClass=person)(uid={_escape(_tidy(uid))}))"\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[이웃] 정리 함수만 부름 (twin)": [
        ('    return f"(&(objectClass=person)(uid={_escape(_tidy(uid))}))"\n',
         '    return f"(&(objectClass=person)(uid={_tidy(uid)}))"\n'),
    ],
    "[빠진 문자] * 를 두고 감": [(_TABLE, '_SPECIAL = {"\\\\": r"\\5c", "(": r"\\28", ")": r"\\29", "\\x00": r"\\00"}\n')],
    "[빠진 문자] 백슬래시를 두고 감": [(_TABLE, '_SPECIAL = {"*": r"\\2a", "(": r"\\28", ")": r"\\29", "\\x00": r"\\00"}\n')],
    "[빠진 문자] NUL 을 두고 감": [(_TABLE, '_SPECIAL = {"\\\\": r"\\5c", "*": r"\\2a", "(": r"\\28", ")": r"\\29"}\n')],
    "[빠진 문자] 괄호만 바꿈": [(_TABLE, '_SPECIAL = {"(": r"\\28", ")": r"\\29"}\n')],
    "[순서] 백슬래시를 * 보다 늦게 바꿈 (이중 이스케이프)": [
        (_ESCAPE, '    return value.replace("*", r"\\2a").replace("(", r"\\28").replace(")", r"\\29").replace("\\x00", r"\\00").replace("\\\\", r"\\5c")\n'),
    ],
    "[길이] 256바이트 정확히도 거절": [(_CHECK, "    if len(uid.encode(\"utf-8\")) >= _MAX_BYTES:\n")],
    "[길이] 바이트 대신 문자 수로 잼": [(_CHECK, "    if len(uid) > _MAX_BYTES:\n")],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[거절] surrogatepass 로 재서 짝 없는 서로게이트를 받음": [
        (_CHECK, '    if len(uid.encode("utf-8", "surrogatepass")) > _MAX_BYTES:\n'),
    ],
    "[길이] 인코딩 확인은 남기고 길이는 문자 수로 잼": [(_CHECK, '    uid.encode("utf-8")\n    if len(uid) > _MAX_BYTES:\n')],
    "[길이] 257바이트까지 받음": [(_CHECK, '    if len(uid.encode("utf-8")) > _MAX_BYTES + 1:\n')],
    "[빠진 문자] ( 를 두고 감": [(_TABLE, '_SPECIAL = {"\\\\": r"\\5c", "*": r"\\2a", ")": r"\\29", "\\x00": r"\\00"}\n')],
    "[빠진 문자] ) 를 두고 감": [(_TABLE, '_SPECIAL = {"\\\\": r"\\5c", "*": r"\\2a", "(": r"\\28", "\\x00": r"\\00"}\n')],
    "[이중 방지] 16진 두 글자가 뒤따르는 백슬래시는 이미 이스케이프로 보고 둠": [
        (_HEAD, _HEAD + "\nimport re\n"),
        (_ESCAPE, '    return re.sub(r"\\\\(?![0-9a-fA-F]{2})|[*()\\x00]", lambda m: f"\\\\{ord(m.group()):02x}", value)\n'),
    ],
    "[정리] 양끝 공백만 strip": [(_TIDY, "    return value.strip()\n")],
    "[비 ASCII] UTF-8 바이트 대신 코드 포인트로 \\XX": [
        (_ESCAPE, '    return "".join(_SPECIAL.get(ch, ch) if ch.isascii() else f"\\\\{ord(ch):02x}" for ch in value)\n'),
    ],
    "[형] str 하위 클래스를 TypeError 로 거절": [
        ("def user_filter(uid: str) -> str:\n", 'def user_filter(uid: str) -> str:\n    if type(uid) is not str:\n        raise TypeError("uid 는 str 이다")\n'),
    ],
    "[빈 값] 정리해 빈 uid 는 모두에 맞는 * 로": [("{_escape(_tidy(uid))}", "{_escape(_tidy(uid)) or '*'}")],
    "[과잉] < > 를 \\< \\> 로 (RFC 4514 식)": [
        (_TABLE, '_SPECIAL = {"\\\\": r"\\5c", "*": r"\\2a", "(": r"\\28", ")": r"\\29", "\\x00": r"\\00", "<": r"\\<", ">": r"\\>"}\n'),
    ],
    "[구문] 닫는 괄호를 하나 더 씀": [(_RETURN, '    return f"(&(objectClass=person)(uid={_escape(_tidy(uid))})))"\n')],
    # 쓰는 단계 점검 - 주장 안인데 원래 증명이 놓치던 약화
    "[길이] 정리한 뒤에 잼": [(_CHECK, '    if len(_tidy(uid).encode("utf-8")) > _MAX_BYTES:\n')],
    "[길이] 이스케이프한 뒤에 잼": [(_CHECK, '    if len(_escape(_tidy(uid)).encode("utf-8")) > _MAX_BYTES:\n')],
    "[정리] ASCII 공백과 NBSP 만 접음": [
        (_HEAD, _HEAD + "\nimport re\n"),
        (_TIDY, '    return re.sub(r"[ \\t\\n\\r\\x0b\\x0c\\xa0]+", " ", value).strip()\n'),
    ],
    "[정리] NFKC 로 정규화": [
        (_HEAD, _HEAD + "\nimport unicodedata\n"),
        (_TIDY, '    return " ".join(unicodedata.normalize("NFKC", value).split())\n'),
    ],
    # 독립 검토 - 거절 탐침의 서로게이트가 U+D800 · U+DFFF 둘뿐이었다 (§3.5 표 「문자 클래스면 구간 전체」)
    "[거절] 길이를 surrogateescape 로 잼 - U+DC80~U+DCFF 를 받음": [(_CHECK, '    if len(uid.encode("utf-8", "surrogateescape")) > _MAX_BYTES:\n')],
    "[거절] 길이를 errors=ignore 로 잼": [(_CHECK, '    if len(uid.encode("utf-8", "ignore")) > _MAX_BYTES:\n')],
    "[거절] 길이를 errors=replace 로 잼": [(_CHECK, '    if len(uid.encode("utf-8", "replace")) > _MAX_BYTES:\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "대문자 16진수 (안전)": [(_TABLE, '_SPECIAL = {"\\\\": r"\\5C", "*": r"\\2A", "(": r"\\28", ")": r"\\29", "\\x00": r"\\00"}\n')],
    "비 ASCII 도 UTF-8 바이트로 이스케이프 (안전)": [
        (_ESCAPE,
         '    return "".join(_SPECIAL.get(ch, ch) if ch.isascii() else "".join(f"\\\\{b:02x}" for b in ch.encode("utf-8")) for ch in value)\n'),
    ],
    "정규식 sub 으로 (안전)": [
        ('"""LDAP 사용자 필터 - 이웃한 두 함수 중 하나만 RFC 4515 의 특수 문자를 이스케이프한다."""\n',
         '"""LDAP 사용자 필터 - 이웃한 두 함수 중 하나만 RFC 4515 의 특수 문자를 이스케이프한다."""\n\nimport re\n'),
        (_ESCAPE, '    return re.sub(r"[\\\\*()\\x00]", lambda m: f"\\\\{ord(m.group()):02x}", value)\n'),
    ],
    "str.translate 로 (안전)": [(_ESCAPE, "    return value.translate(str.maketrans(_SPECIAL))\n")],
    "& 안의 두 비교 순서를 바꿈 (안전)": [(_RETURN, '    return f"(&(uid={_escape(_tidy(uid))})(objectClass=person))"\n')],
    "모든 글자를 UTF-8 바이트 \\XX 로 (안전)": [(_ESCAPE, '    return "".join(f"\\\\{b:02x}" for b in value.encode("utf-8"))\n')],
    "정규식 \\s+ 로 공백 정리 (안전)": [
        (_HEAD, _HEAD + "\nimport re\n"),
        (_TIDY, '    return re.sub(r"\\s+", " ", value).strip()\n'),
    ],
    # 독립 검토 - RFC 4512 는 속성 이름과 objectClass 값(descr)의 대소문자를 가리지 않는다
    "objectclass 를 소문자로 (안전)": [(_RETURN, _RETURN.replace("objectClass", "objectclass"))],
    "속성 이름 UID 를 대문자로 (안전)": [(_RETURN, _RETURN.replace("(uid=", "(UID="))],
    "objectClass 값을 Person 으로 (안전)": [(_RETURN, _RETURN.replace("=person)", "=Person)"))],
    "이스케이프한 뒤 정리 (안전)": [(_RETURN, _RETURN.replace("{_escape(_tidy(uid))}", "{_tidy(_escape(uid))}"))],
}

RACY: dict[str, list[tuple[str, str]]] = {}
