"""문법 상한의 변이 - 주장 축별 약화와 의미를 보존하는 변형을 비교한다."""

_PATTERN = 'r"(?:0|[1-9][0-9]{0,3})"'
_CHECK = "    if _COUNT.fullmatch(count_text) is None:"
_ERROR = '        raise ValueError("invalid padding count")'
_ALLOCATE = "    return bytearray(int(count_text, 10))"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "전체 문자열: 접두사만 검사": [
        ("_COUNT.fullmatch(count_text)", "_COUNT.match(count_text)"),
    ],
    "자리수 상한: 다섯 자리 허용": [
        (_PATTERN, 'r"(?:0|[1-9][0-9]{0,4})"'),
    ],
    "전체 문자열: 마지막 개행 허용": [
        (_PATTERN, 'r"(?:0|[1-9][0-9]{0,3})$"'),
        ("_COUNT.fullmatch(count_text)", "_COUNT.match(count_text)"),
    ],
    "표준 표기: 선행 0 허용": [
        (_PATTERN, 'r"[0-9]{1,4}"'),
    ],
    "표준 표기: 양수 부호 허용": [
        (_PATTERN, r'r"\+?(?:0|[1-9][0-9]{0,3})"'),
    ],
    "표준 표기: 음의 0 허용": [
        (_PATTERN, 'r"(?:-?0|[1-9][0-9]{0,3})"'),
    ],
    "표준 표기: 공백 제거 후 검사": [
        (_CHECK, "    count_text = count_text.strip()\n" + _CHECK),
    ],
    "표준 표기: 밑줄 제거 후 검사": [
        (_CHECK, '    count_text = count_text.replace("_", "")\n' + _CHECK),
    ],
    "ASCII: 후속 Unicode 숫자 허용": [
        (_PATTERN, r'r"(?:0|[1-9]\d{0,3})"'),
    ],
    "ASCII: 첫 자리 Unicode 숫자 허용": [
        (_PATTERN, r'r"(?:0|[^\D0]\d{0,3})"'),
    ],
    "빈 문자열: 누락 필드를 0으로 취급": [
        (_CHECK, '    count_text = count_text or "0"\n' + _CHECK),
    ],
    "유효한 0: 거절": [
        (_PATTERN, 'r"[1-9][0-9]{0,3}"'),
    ],
    "유효한 네 자리: 세 자리까지만 허용": [
        (_PATTERN, 'r"(?:0|[1-9][0-9]{0,2})"'),
    ],
    "유효한 상한: 9999만 거절": [
        (_CHECK, '    if count_text == "9999":\n' + _ERROR + "\n" + _CHECK),
    ],
    "값 보존: 한 바이트 더 할당": [
        (_ALLOCATE, "    return bytearray(int(count_text, 10) + 1)"),
    ],
    "값 보존: 하위 8비트만 사용": [
        (_ALLOCATE, "    return bytearray(int(count_text, 10) & 255)"),
    ],
    "초기 바이트: 0 대신 1": [
        (_ALLOCATE, r'    return bytearray(b"\x01") * int(count_text, 10)'),
    ],
    "평범한 하위 타입: 정확한 str만 허용": [
        (_CHECK, '    if type(count_text) is not str:\n' + _ERROR + "\n" + _CHECK),
    ],
    "표준 Enum 하위 타입: str 변환으로 값 손실": [
        (_CHECK, "    count_text = str(count_text)\n" + _CHECK),
    ],
    "거절 시점: 하위 할당을 먼저 실행": [
        (_CHECK, "    _allocate(count_text)\n" + _CHECK),
    ],
    "매 호출: 첫 호출 이후 검사 생략": [
        (_CHECK, '    global _visited\n    if globals().get("_visited", False):\n        return _allocate(count_text)\n    _visited = True\n' + _CHECK),
    ],
    "최적화 실행: assert에 의존": [
        (_CHECK + "\n" + _ERROR,
         '    assert _COUNT.fullmatch(count_text) is not None, "invalid padding count"'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "거절 예외 종류는 계약 밖": [
        (_ERROR, '        raise RuntimeError("invalid padding count")'),
    ],
    "정규식 import 별칭": [
        ("import re", "import re as regex"),
        ("_COUNT = re.compile", "_COUNT = regex.compile"),
    ],
    "끝 경계를 명시한 동등 문법": [
        (_PATTERN, r'r"(?:0|[1-9][0-9]{0,3})\Z"'),
        ("_COUNT.fullmatch(count_text)", "_COUNT.match(count_text)"),
    ],
    "동등한 길이 대안 나열": [
        (_PATTERN, 'r"(?:0|[1-9]|[1-9][0-9]|[1-9][0-9]{2}|[1-9][0-9]{3})"'),
    ],
    "동등한 버퍼 생성": [
        (_ALLOCATE, "    return bytearray([0]) * int(count_text, 10)"),
    ],
    "bytearray의 평범한 하위 타입": [
        ("def _allocate(count_text: str) -> bytearray:",
         "class Buffer(bytearray):\n    pass\n\n\ndef _allocate(count_text: str) -> bytearray:"),
        (_ALLOCATE, "    return Buffer(int(count_text, 10))"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
