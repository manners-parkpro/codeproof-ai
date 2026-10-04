"""D128 변이 - 쓰는 단계 11개 · 쓰는 단계 점검 14개 · 독립 검토 4개 (약화 19 · 안전 10 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_PATTERN = '_DIGITS = re.compile(r"[0-9]*")\n'
_HEAD = "    head = _DIGITS.match(tag).group()\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[패턴] + 로 한 자 이상을 요구 (twin)": [(_PATTERN, '_DIGITS = re.compile(r"[0-9]+")\n')],
    "[패턴] \\d 로 유니코드 숫자까지": [(_PATTERN, '_DIGITS = re.compile(r"\\d*")\n')],
    "[패턴] [1-9] 로 0 을 빠뜨림": [(_PATTERN, '_DIGITS = re.compile(r"[1-9]*")\n')],
    "[맞춤] fullmatch 로 전체를 요구": [(_HEAD, "    head = _DIGITS.fullmatch(tag).group()\n")],
    "[나머지] rest 를 strip": [("    return head, tag[len(head) :]\n", "    return head, tag[len(head) :].strip()\n")],
    "[머리] 앞의 0 을 지움": [(_HEAD, '    head = _DIGITS.match(tag).group().lstrip("0")\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[패턴] 부호를 숫자에 붙임": [(_PATTERN, '_DIGITS = re.compile(r"[+-]?[0-9]*")\n')],
    "[머리] 첫 글자로 갈라 빈 꼬리표에서 IndexError": [
        (_HEAD, '    head = _DIGITS.match(tag).group() if tag[0] in "0123456789" else ""\n'),
    ],
    "[패턴] 수량자 상한 {0,64}": [(_PATTERN, '_DIGITS = re.compile(r"[0-9]{0,64}")\n')],
    "[형] str 하위 클래스를 TypeError 로 거절": [
        ("def split_version(tag: str) -> tuple[str, str]:\n",
         'def split_version(tag: str) -> tuple[str, str]:\n    if type(tag) is not str:\n        raise TypeError("tag 는 str 이다")\n'),
    ],
    "[패턴] 점까지 head 로": [(_PATTERN, '_DIGITS = re.compile(r"[0-9.]*")\n')],
    # 쓰는 단계 점검 - 주장 안인데 원래 증명이 놓치던 약화
    "[어떤 tag 든] UTF-8 바이트 위에서 맞춤": [
        (_HEAD, '    head = re.match(rb"[0-9]*", tag.encode("utf-8")).group().decode("ascii")\n'),
    ],
    "[패턴] 숫자 3 · 5 · 6 · 8 을 빠뜨림": [(_PATTERN, '_DIGITS = re.compile(r"[0-24-79]*")\n')],
    "[나머지] PEP 440 식 소문자로": [("    return head, tag[len(head) :]\n", "    return head, tag[len(head) :].lower()\n")],
    "[나머지] NFC 로 정규화한 뒤 자름": [
        ("import re\n", "import re\nimport unicodedata\n"),
        (_HEAD, '    tag = unicodedata.normalize("NFC", tag)\n    head = _DIGITS.match(tag).group()\n'),
    ],
    "[패턴] 수량자 상한 {0,10000}": [(_PATTERN, '_DIGITS = re.compile(r"[0-9]{0,10000}")\n')],
    # 독립 검토 - 숫자 뒤 글자를 몇 개로만 쳐서 자릿수 구분자를 넣은 문자 클래스가 지나갔다 (§3.5 표 「문자 클래스면 구간 전체」)
    "[문자 클래스] 밑줄 자릿수 구분자 [0-9_]": [('_DIGITS = re.compile(r"[0-9]*")\n', '_DIGITS = re.compile(r"[0-9_]*")\n')],
    "[문자 클래스] 쉼표 자릿수 구분자 [0-9,]": [('_DIGITS = re.compile(r"[0-9]*")\n', '_DIGITS = re.compile(r"[0-9,]*")\n')],
    "[문자 클래스] 홑따옴표 자릿수 구분자 [0-9\']": [('_DIGITS = re.compile(r"[0-9]*")\n', '_DIGITS = re.compile(r"[0-9\']*")\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "match 가 None 이면 빈 문자열 (안전)": [
        (_HEAD, '    found = _DIGITS.match(tag)\n    head = found.group() if found else ""\n'),
    ],
    "search 로 (안전)": [(_HEAD, "    head = _DIGITS.search(tag).group()\n")],
    "re.ASCII 의 \\d 로 (안전)": [(_PATTERN, '_DIGITS = re.compile(r"\\d*", re.ASCII)\n')],
    "정규식 없이 takewhile 로 (안전)": [
        ("import re\n", "import itertools\nimport re\n"),
        (_HEAD, '    head = "".join(itertools.takewhile(lambda ch: ch in "0123456789", tag))\n'),
    ],
    "결과를 리스트로 (안전)": [("    return head, tag[len(head) :]\n", "    return [head, tag[len(head) :]]  # type: ignore[return-value]\n")],
    "lstrip 으로 앞자리 길이를 잼 (안전)": [(_HEAD, '    head = tag[: len(tag) - len(tag.lstrip("0123456789"))]\n')],
    "removeprefix 로 rest (안전)": [("    return head, tag[len(head) :]\n", "    return head, tag.removeprefix(head)\n")],
    "코드 포인트 비교로 첫 비숫자 위치 (안전)": [
        (_HEAD, '    head = tag[: next((i for i, ch in enumerate(tag) if not "0" <= ch <= "9"), len(tag))]\n'),
    ],
    "+ 패턴에 None 처리 (안전)": [
        (_PATTERN, '_DIGITS = re.compile(r"[0-9]+")\n'),
        (_HEAD, '    found = _DIGITS.match(tag)\n    head = found.group() if found else ""\n'),
    ],
    "re.IGNORECASE 를 더함 (안전)": [('_DIGITS = re.compile(r"[0-9]*")\n', '_DIGITS = re.compile(r"[0-9]*", re.IGNORECASE)\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
