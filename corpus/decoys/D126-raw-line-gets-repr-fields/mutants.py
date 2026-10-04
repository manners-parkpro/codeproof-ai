"""D126 변이 - 쓰는 단계 11개 · 쓰는 단계 점검 24개 · 독립 검토 4개 · 교차 3개 (약화 31 · 안전 11 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_CALL = '    _write_raw_line(sink, f"user={str.__str__(user)!a} action={str.__str__(action)!a}")\n'
_WRITE = '    sink.write(line + "\\n")\n'
_HEAD = "from typing import TextIO\n"
# 손으로 쓴 escaper - 아래 문자 클래스만 \uXXXX 로 바꾸고 백슬래시 · 따옴표는 다룬다
_QUOTE = (
    "\n\ndef _quote(value: str) -> str:\n"
    "    body = value.replace(\"\\\\\", \"\\\\\\\\\").replace(\"'\", \"\\\\'\")\n"
    "    return \"'\" + _CTRL.sub(_code, body) + \"'\"\n\n\n"
    "def _code(m: re.Match[str]) -> str:\n"
    "    n = ord(m.group())\n"
    "    return f\"\\\\u{n:04x}\" if n <= 0xFFFF else f\"\\\\U{n:08x}\"\n"
)


def _hand(pattern: str) -> list[tuple[str, str]]:
    """repr 대신 손 escaper 로 감싸는 변이 - pattern 은 이스케이프할 문자 클래스."""
    return [
        (_HEAD, "import re\n" + _HEAD),
        (_CALL, '    _write_raw_line(sink, f"user={_quote(user)} action={_quote(action)}")\n'
                f"\n\n_CTRL = re.compile(r\"{pattern}\")" + _QUOTE),
    ]


WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[감싸기] 감싸지 않고 그대로 (twin)": [(_CALL, '    _write_raw_line(sink, f"user={user} action={action}")\n')],
    "[감싸기] user 만 감쌈": [(_CALL, '    _write_raw_line(sink, f"user={user!a} action={action}")\n')],
    "[감싸기] \\n 만 공백으로 바꾸고 repr": [
        (_CALL, "    clean = [part.replace(chr(10), ' ') for part in (user, action)]\n"
                '    _write_raw_line(sink, f"user={clean[0]!r} action={clean[1]!r}")\n'),
    ],
    "[감싸기] 따옴표로만 감쌈": [(_CALL, "    _write_raw_line(sink, f\"user='{user}' action='{action}'\")\n")],
    "[감싸기] splitlines 로 줄만 이어붙임 (계획안)": [
        (_CALL, "    clean = [' '.join(part.splitlines()) for part in (user, action)]\n"
                '    _write_raw_line(sink, f"user={clean[0]} action={clean[1]}")\n'),
    ],
    "[도우미] 줄 끝을 두 번": [(_WRITE, '    sink.write(line + "\\n\\n")\n')],
    "[도우미] 줄 끝 없이": [(_WRITE, "    sink.write(line)\n")],
    # ASCII - repr 계열은 인쇄 가능한 비 ASCII 를 그대로 둔다 (쓰는 단계 점검)
    "[ASCII] repr(!r) 로 감쌈 - 한글이 그대로": [(_CALL, '    _write_raw_line(sink, f"user={user!r} action={action!r}")\n')],
    "[ASCII] %r 서식": [(_CALL, '    _write_raw_line(sink, "user=%r action=%r" % (user, action))\n')],
    "[ASCII] user 는 repr · action 은 ascii": [(_CALL, '    _write_raw_line(sink, f"user={user!r} action={action!a}")\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[감싸기] 손 escaper 가 \\x85 · U+2028 · U+2029 를 빠뜨림": _hand("[\\x00-\\x1f\\x7f\\ud800-\\udfff]"),
    "[감싸기] 손 escaper 가 짝 없는 서로게이트를 빠뜨림": _hand("[\\x00-\\x1f\\x7f-\\x9f\\u2028\\u2029]"),
    "[감싸기] 손 escaper 가 NUL 을 빠뜨림": _hand("[\\x01-\\x1f\\x7f-\\x9f\\u2028\\u2029\\ud800-\\udfff]"),
    "[감싸기] unicode_escape 로 감싸고 따옴표를 빠뜨림": [
        (_CALL, "    _write_raw_line(sink, \"user='%s' action='%s'\" % tuple(v.encode(\"unicode_escape\").decode(\"ascii\") for v in (user, action)))\n"),
    ],
    "[칸] 역슬래시를 슬래시로 바꿔 씀": [
        (_CALL, "    _write_raw_line(sink, f\"user={user.replace(chr(92), '/')!a} action={action.replace(chr(92), '/')!a}\")\n"),
    ],
    "[칸] 칸마다 1024 자로 자름": [(_CALL, '    _write_raw_line(sink, f"user={user[:1024]!a} action={action[:1024]!a}")\n')],
    "[칸] 빈 값은 - 로 씀": [(_CALL, "    _write_raw_line(sink, f\"user={user or '-'!a} action={action or '-'!a}\")\n")],
    "[형] 정확히 str 이 아니면 거절": [
        (_CALL, '    if type(user) is not str or type(action) is not str:\n        raise TypeError("user · action 은 str")\n' + _CALL),
    ],
    "[칸] 탭을 공백으로 펼침": [(_CALL, '    _write_raw_line(sink, f"user={user.expandtabs()!a} action={action.expandtabs()!a}")\n')],
    "[칸] action 만 1024 자로 자름": [(_CALL, '    _write_raw_line(sink, f"user={user!a} action={action[:1024]!a}")\n')],
    "[칸] user 만 1024 자로 자름": [(_CALL, '    _write_raw_line(sink, f"user={user[:1024]!a} action={action!a}")\n')],
    "[도우미] 줄 끝을 \\r 로": [(_WRITE, '    sink.write(line + "\\r")\n')],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[칸] 소문자로 접음": [(_CALL, '    _write_raw_line(sink, f"user={user.lower()!a} action={action.lower()!a}")\n')],
    "[칸] NFKC 로 정규화": [
        (_HEAD, "import unicodedata\n" + _HEAD),
        (_CALL, '    _write_raw_line(sink, f"user={unicodedata.normalize(\'NFKC\', user)!a} action={unicodedata.normalize(\'NFKC\', action)!a}")\n'),
    ],
    "[감싸기] 손 escaper 가 백슬래시를 이스케이프하지 않음": [
        (_HEAD, "import re\n" + _HEAD),
        (_CALL, '    _write_raw_line(sink, f"user={_quote(user)} action={_quote(action)}")\n'
                "\n\n_CTRL = re.compile(r\"[^\\x20-\\x7e]\")\n\n\ndef _quote(value: str) -> str:\n"
                "    body = value.replace(\"'\", \"\\\\'\")\n"
                "    return \"'\" + _CTRL.sub(lambda m: f\"\\\\u{ord(m.group()):04x}\", body) + \"'\"\n"),
    ],
    "[도우미] 줄 끝을 \\r\\n 으로": [(_WRITE, '    sink.write(line + "\\r\\n")\n')],
    # 독립 검토 - repr 을 바꾼 표준 라이브러리 하위 타입(StrEnum · http.HTTPMethod)을 치지 않았다
    "[하위 타입] str() 없이 !a - StrEnum 은 repr 이 <Action.GRANT: 'grant'> (검토 전 decoy)": [
        (_CALL, '    _write_raw_line(sink, f"user={user!a} action={action!a}")\n'),
    ],
    "[감싸기] !r 뒤 ascii replace - 비 ASCII 가 ? 로": [
        (_CALL, '    _write_raw_line(sink, ("user=%r action=%r" % (str.__str__(user), str.__str__(action))).encode("ascii", "replace").decode("ascii"))\n'),
    ],
    "[감싸기] json.dumps(ensure_ascii) - 이모지가 서로게이트 둘로": [
        (_HEAD, "import json\n" + _HEAD),
        (_CALL, '    _write_raw_line(sink, f"user={json.dumps(str.__str__(user))} action={json.dumps(str.__str__(action))}")\n'),
    ],
    # 교차 렌즈 - (str, Enum) 혼합형은 str() 이 값 대신 이름(Role.ADMIN)을 돌려준다
    "[하위 타입] str() 로 바꿈 - (str, Enum) 혼합형은 이름이 기록 (교차 렌즈 전 decoy)": [
        (_CALL, '    _write_raw_line(sink, f"user={str(user)!a} action={str(action)!a}")\n'),
    ],
    "[하위 타입] action 만 str() 로 바꿈": [
        (_CALL, '    _write_raw_line(sink, f"user={str.__str__(user)!a} action={str(action)!a}")\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "ascii() 를 직접 부름 (안전)": [(_CALL, '    _write_raw_line(sink, f"user={ascii(str.__str__(user))} action={ascii(str.__str__(action))}")\n')],
    "%a 서식 (안전)": [(_CALL, '    _write_raw_line(sink, "user=%a action=%a" % (str.__str__(user), str.__str__(action)))\n')],
    "format 의 !a (안전)": [(_CALL, '    _write_raw_line(sink, "user={!a} action={!a}".format(str.__str__(user), str.__str__(action)))\n')],
    "도우미가 print(file=sink) 로 씀 (안전)": [(_WRITE, "    print(line, file=sink)\n")],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    "기록 앞에 audit 머리말 (안전)": [(_CALL, '    _write_raw_line(sink, f"audit user={str.__str__(user)!a} action={str.__str__(action)!a}")\n')],
    "= 뒤에 공백 하나 (안전)": [(_CALL, '    _write_raw_line(sink, f"user= {str.__str__(user)!a} action= {str.__str__(action)!a}")\n')],
    "도우미가 writelines 로 씀 (안전)": [(_WRITE, '    sink.writelines((line, "\\n"))\n')],
    "unicode_escape 로 감싸고 홑따옴표도 이스케이프 (안전)": [
        (_CALL, "    _write_raw_line(sink, \"user='%s' action='%s'\" % tuple(v.encode(\"unicode_escape\").decode(\"ascii\").replace(\"'\", \"\\\\'\") for v in (user, action)))\n"),
    ],
    "손 escaper 가 인쇄 가능한 ASCII 밖을 모두 \\u 로 (안전)": [
        (_HEAD, "import re\n" + _HEAD),
        (_CALL, '    _write_raw_line(sink, f"user={_quote(user)} action={_quote(action)}")\n'
                "\n\n_CTRL = re.compile(r\"[^\\x20-\\x7e]\")" + _QUOTE),
    ],
    "repr(str.__str__()) 뒤 backslashreplace 로 ASCII 화 (안전)": [
        (_CALL, '    _write_raw_line(sink, "user=" + repr(str.__str__(user)).encode("ascii", "backslashreplace").decode("ascii")'
                ' + " action=" + repr(str.__str__(action)).encode("ascii", "backslashreplace").decode("ascii"))\n'),
    ],
    # 교차 렌즈 - 밑 문자열을 얻는 다른 길
    "전체 슬라이스로 밑 문자열 (안전)": [(_CALL, '    _write_raw_line(sink, f"user={user[:]!a} action={action[:]!a}")\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
