"""D150 변이 - 쓰는 단계 16개 · 쓰는 단계 점검 18개 · 독립 검토 3개 (약화 26 · 안전 11 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_PATTERN = '_MONTH = re.compile(r"0?[1-9]|1[0-2]")\n'
_CHECK = "    if _MONTH.fullmatch(text) is None:\n"
_BODY = _CHECK + '        raise ValueError(f"달 번호가 아니다: {text!r}")\n    return int(text)\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[검사] 빈 문자열만 막음 (twin)": [(_CHECK, "    if not text:\n")],
    "[범위] 0 을 받음": [(_PATTERN, '_MONTH = re.compile(r"0?[0-9]|1[0-2]")\n')],
    "[범위] 13 을 받음": [(_PATTERN, '_MONTH = re.compile(r"0?[1-9]|1[0-3]")\n')],
    "[범위 끝] 12 를 막음": [(_PATTERN, '_MONTH = re.compile(r"0?[1-9]|1[01]")\n')],
    "[앞자리 0] 여럿을 받음": [(_PATTERN, '_MONTH = re.compile(r"0*[1-9]|1[0-2]")\n')],
    "[앞자리 0] 하나도 받지 않음": [(_PATTERN, '_MONTH = re.compile(r"[1-9]|1[0-2]")\n')],
    "[줄바꿈] match 와 $": [(_CHECK, '    if re.match(r"(?:0?[1-9]|1[0-2])$", text) is None:\n')],
    "[공백] 앞뒤 공백을 걷고 맞춤": [(_CHECK, "    if _MONTH.fullmatch(text.strip()) is None:\n")],
    "[유니코드 숫자] \\d 로 맞춤": [(_PATTERN, '_MONTH = re.compile(r"0?(?!0)\\d|1[0-2]")\n')],
    "[형식] int() 뒤 범위만 확인": [
        (_BODY, '    month = int(text)\n    if not 1 <= month <= 12:\n        raise ValueError(f"달 번호가 아니다: {text!r}")\n    return month\n'),
    ],
    "[검사] ASCII 인지만 확인 - 범위는 int 와 첨자에 맡김": [(_CHECK, "    if not text.isascii():\n")],
    "[차례] 이름이 하나 밀림": [("    return _NAMES[_month(text) - 1]\n", "    return _NAMES[_month(text) % 12]\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[그 밖] 영어 달 이름도 받음': [('def month_name(text: str) -> str:\n', 'def month_name(text: str) -> str:\n    if text in _NAMES:\n        return text\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[하위 타입] str 이 아닌 값은 int 뒤 범위만 확인': [('    if _MONTH.fullmatch(text) is None:\n', '    if type(text) is not str:\n        month = int(text)\n        if not 1 <= month <= 12:\n            raise ValueError(f"달 번호가 아니다: {text!r}")\n        return month\n    if _MONTH.fullmatch(text) is None:\n')],
    '[하위 타입] str() 로 바꿔 맞춤': [('def _month(text: str) -> int:\n', 'def _month(text: str) -> int:\n    text = str(text)\n')],
    '[빈 문자열] 빈 값은 1월': [('    if _MONTH.fullmatch(text) is None:\n', '    if text and _MONTH.fullmatch(text) is None:\n'), ('    return int(text)\n', '    return int(text or "1")\n')],
    '[범위] 두 자리 달을 [12][0-2] 로': [('_MONTH = re.compile(r"0?[1-9]|1[0-2]")\n', '_MONTH = re.compile(r"0?[1-9]|[12][0-2]")\n')],
    '[부호] + 부호를 받음': [('_MONTH = re.compile(r"0?[1-9]|1[0-2]")\n', '_MONTH = re.compile(r"\\+?(?:0?[1-9]|1[0-2])")\n')],
    '[공백] 공백과 탭만 걷음': [('    if _MONTH.fullmatch(text) is None:\n', '    if _MONTH.fullmatch(text.strip(" \\t")) is None:\n')],
    '[밑줄] 자릿수 밑줄을 버림': [('    if _MONTH.fullmatch(text) is None:\n', '    if _MONTH.fullmatch(text.replace("_", "")) is None:\n')],
    '[소수점] .0 을 받음': [('_MONTH = re.compile(r"0?[1-9]|1[0-2]")\n', '_MONTH = re.compile(r"(?:0?[1-9]|1[0-2])(?:\\.0)?")\n'), ('    return int(text)\n', '    return int(float(text))\n')],
    '[NUL] NUL 에서 끊음': [('def _month(text: str) -> int:\n', 'def _month(text: str) -> int:\n    text = text.split("\\0")[0]\n')],
    '[길이] 긴 입력은 앞 두 글자만 봄': [('def _month(text: str) -> int:\n', 'def _month(text: str) -> int:\n    if len(text) > 64:\n        text = text[:2]\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[꼴] 앞의 BOM 을 걷어냄 - UTF-8 로 읽은 CSV 첫 칸을 고치는 흔한 꼴': [('def _month(text: str) -> int:\n', 'def _month(text: str) -> int:\n    text = text.lstrip(chr(0xFEFF))\n')],
    '[꼴] 서식 문자(Cf)를 지움 - 0 + U+200B + 7 이 July': [('def _month(text: str) -> int:\n', 'def _month(text: str) -> int:\n    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")\n'), ('import re\n', 'import re\nimport unicodedata\n')],
    '[꼴] 줄 끝의 C1 제어(NEL)와 줄 구분자를 걷어냄': [('def _month(text: str) -> int:\n', 'def _month(text: str) -> int:\n    text = text.rstrip(chr(0x85) + chr(0x2028) + chr(0x2029))\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "re.ASCII 를 붙임 (안전)": [(_PATTERN, '_MONTH = re.compile(r"0?[1-9]|1[0-2]", re.ASCII)\n')],
    "match 와 \\Z (안전)": [(_CHECK, '    if re.match(r"(?:0?[1-9]|1[0-2])\\Z", text) is None:\n')],
    "정해 둔 문자열 집합으로 (안전)": [
        (_PATTERN, _PATTERN + '_TEXTS = frozenset([f"{m}" for m in range(1, 13)] + [f"0{m}" for m in range(1, 10)])\n'),
        (_CHECK, "    if text not in _TEXTS:\n"),
    ],
    "맞춘 뒤 범위를 한 번 더 확인 (안전)": [
        ("    return int(text)\n", '    month = int(text)\n    if not 1 <= month <= 12:\n        raise ValueError(f"달 번호가 아니다: {text!r}")\n    return month\n'),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '[예외 타입] ValueError 하위 클래스': [('def _month(text: str) -> int:\n', 'class MonthError(ValueError):\n    pass\n\n\ndef _month(text: str) -> int:\n'), ('        raise ValueError(f"달 번호가 아니다: {text!r}")\n', '        raise MonthError(f"달 번호가 아니다: {text!r}")\n')],
    '[컨테이너] _NAMES 를 list 로': [('_NAMES = (\n', '_NAMES = [\n'), ('    "July", "August", "September", "October", "November", "December",\n)\n', '    "July", "August", "September", "October", "November", "December",\n]\n')],
    '[import 꼴] from re import compile': [('import re\n', 'from re import compile as _compile\n'), ('_MONTH = re.compile(', '_MONTH = _compile(')],
    '[다른 구현] 정규식 없이 글자를 직접 확인': [('    if _MONTH.fullmatch(text) is None:\n', '    if not ((len(text) == 1 and "1" <= text <= "9") or (len(text) == 2 and ((text[0] == "0" and "1" <= text[1] <= "9") or (text[0] == "1" and "0" <= text[1] <= "2")))):\n')],
    '[다른 구현] \\d 에 re.ASCII': [('_MONTH = re.compile(r"0?[1-9]|1[0-2]")\n', '_MONTH = re.compile(r"0?(?!0)\\d|1[0-2]", re.ASCII)\n')],
    '[컨테이너] dict 로 찾음': [('    return _NAMES[_month(text) - 1]\n', '    return dict(enumerate(_NAMES, start=1))[_month(text)]\n')],
    '[하위 타입] str.__str__ 로 값만 꺼냄': [('def _month(text: str) -> int:\n', 'def _month(text: str) -> int:\n    text = str.__str__(text)\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
