"""주장 축별 변이 - 전체 문법, 경계, 채널 값, 하위 타입과 반복을 교차 검증한다."""

_PATTERN = 'r"#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})"'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "일치 실패 가드 삭제": [("    if match is None:\n        return None\n", "")],
    "assert로 거절": [("    if match is None:\n        return None", "    assert match is not None")],
    "실패를 검정으로 대체": [("        return None", "        return (0, 0, 0)")],
    "빈 문자열만 거절": [("if match is None:", "if not text:")],
    "접두사만 일치": [("_RGB.fullmatch(text)", "_RGB.match(text)")],
    "부분 문자열도 수용": [("_RGB.fullmatch(text)", "_RGB.search(text)")],
    "공백 제거 뒤 검사": [("_RGB.fullmatch(text)", "_RGB.fullmatch(text.strip())")],
    "대문자 누락": [(_PATTERN, 'r"#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})"')],
    "소문자 누락": [(_PATTERN, 'r"#?([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})"')],
    "유니코드 십진수도 수용": [(_PATTERN, 'r"#?([\\da-fA-F]{2})([\\da-fA-F]{2})([\\da-fA-F]{2})"')],
    "짧은 채널도 수용": [(_PATTERN, 'r"#?([0-9a-fA-F]{1,2})([0-9a-fA-F]{1,2})([0-9a-fA-F]{1,2})"')],
    "샵을 필수로 변경": [('r"#?(', 'r"#(')],
    "샵 여러 개 허용": [('r"#?(', 'r"#*(')],
    "빨강 파랑 뒤바꿈": [
        ("int(match.group(1), 16),", "int(match.group(3), 16),"),
        ("int(match.group(3), 16),\n    )", "int(match.group(1), 16),\n    )"),
    ],
    "초록 십진수 변환": [("int(match.group(2), 16)", "int(match.group(2), 10)")],
    "채널 최댓값 누락": [("int(match.group(3), 16)", "min(254, int(match.group(3), 16))")],
    "채널 최솟값 누락": [("int(match.group(1), 16)", "max(1, int(match.group(1), 16))")],
    "튜플 대신 목록 반환": [("    return (\n", "    return [\n"), ("    )\n", "    ]\n")],
    "하위 타입 배제": [
        ("    match = _RGB.fullmatch(text)", "    if type(text) is not str:\n        return None\n    match = _RGB.fullmatch(text)"),
    ],
    "Enum 표시 이름으로 변환": [("_RGB.fullmatch(text)", "_RGB.fullmatch(str(text))")],
    "이전 유효 결과 재사용": [
        ("    match = _RGB.fullmatch(text)", "    match = getattr(parse_rgb, '_last', None) or _RGB.fullmatch(text)\n    parse_rgb._last = match"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "매치 진릿값 검사": [("if match is None:", "if not match:")],
    "실패 시 명시적 빈 반환": [("        return None", "        return")],
    "전체 문자열 슬라이스": [("_RGB.fullmatch(text)", "_RGB.fullmatch(text[:])")],
    "구체 str 검사로 제한하지 않는 변환": [("_RGB.fullmatch(text)", "_RGB.fullmatch(str.__str__(text))")],
    "ASCII 대소문자 플래그": [(_PATTERN, 'r"#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})", re.IGNORECASE | re.ASCII')],
    "매치 인덱스로 채널 접근": [("match.group(1)", "match[1]"), ("match.group(2)", "match[2]"), ("match.group(3)", "match[3]")],
    "실패 분기 안에만 예외를 흡수": [
        ("        return None", "        try:\n            raise ValueError(text)\n        except ValueError:\n            return None"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
