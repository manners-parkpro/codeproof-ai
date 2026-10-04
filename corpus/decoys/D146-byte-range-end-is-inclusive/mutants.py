"""D146 변이 - 쓰는 단계 12개 · 쓰는 단계 점검 31개 · 독립 검토 1개 (약화 33 · 안전 11 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_RE = '_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n'
_CHECK = "    if first > last or first >= size:\n"
_STOP = "    return first, min(last, size - 1) + 1\n"
_MATCH = "    match = _RANGE.fullmatch(header)\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[반열린] 끝에 1 을 더하지 않음 (twin)": [(_STOP, "    return first, min(last, size - 1)\n")],
    "[반열린] 시작에서 1 을 뺌": [(_STOP, "    return max(first - 1, 0), min(last, size - 1) + 1\n")],
    "[거절] a > b 를 받음": [(_CHECK, "    if first >= size:\n")],
    "[거절] 시작이 끝 너머여도 받음": [(_CHECK, "    if first > last:\n")],
    "[꼴] match - 뒤의 글자를 받음": [(_MATCH, "    match = _RANGE.match(header)\n")],
    "[꼴] \\d 에 re.ASCII 없이 - ASCII 가 아닌 숫자도": [(_RE, '_RANGE = re.compile(r"bytes=(\\d{1,18})-(\\d{1,18})", re.IGNORECASE)\n')],
    "[꼴] 자릿수 제한 없음": [(_RE, '_RANGE = re.compile(r"bytes=([0-9]+)-([0-9]+)", re.IGNORECASE | re.ASCII)\n')],
    "[꼴] 단위의 대소문자를 가림": [(_RE, '_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})")\n')],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[꼴] 시작은 17자리까지': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,17})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] 단위는 세 철자만': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"(?:bytes|BYTES|Bytes)=([0-9]{1,18})-([0-9]{1,18})")\n')],
    '[꼴] NFKC 로 정규화한 뒤 맞춤': [('import re\n', 'import re\nimport unicodedata\n'), ('    match = _RANGE.fullmatch(header)\n', '    match = _RANGE.fullmatch(unicodedata.normalize("NFKC", header))\n')],
    '[꼴] bytes 하위 클래스 본문을 거절': [('    return body[start:stop]\n', '    if type(body) is not bytes:\n        raise TypeError(body)\n    return body[start:stop]\n')],
    '[꼴] = 앞의 공백을 받음': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes\\s*=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] - 앞뒤의 공백을 받음': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,18})\\s*-\\s*([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] 끝의 빈 목록 원소(쉼표)를 받음': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18}),?", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] 끝 없는 bytes=a 를 한 바이트로': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,18})(?:-([0-9]{1,18}))?", re.IGNORECASE | re.ASCII)\n'), ('    first, last = int(match[1]), int(match[2])\n', '    first, last = int(match[1]), int(match[2] or match[1])\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[꼴] 앞자리 0 을 거절': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=(0|[1-9][0-9]{0,17})-(0|[1-9][0-9]{0,17})", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] 시작은 2자리까지': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,2})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n')],
    '[거절] 끝 너머의 b 를 거절': [('    if first > last or first >= size:\n', '    if first > last or first >= size or last >= size:\n')],
    '[꼴] 끝은 17자리까지': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,17})", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] str 하위 클래스를 거절': [('    match = _RANGE.fullmatch(header)\n', '    if type(header) is not str:\n        raise TypeError(header)\n    match = _RANGE.fullmatch(header)\n')],
    '[거절] 빈 본문만 거절 - 시작이 끝 너머여도 받음': [('    if first > last or first >= size:\n', '    if first > last or size == 0:\n')],
    '[꼴] 열린 끝 bytes=a- 을 받음': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{0,18})", re.IGNORECASE | re.ASCII)\n'), ('    first, last = int(match[1]), int(match[2])\n', '    first, last = int(match[1]), int(match[2] or size - 1)\n')],
    '[꼴] 여러 범위 중 첫 범위만': [('    match = _RANGE.fullmatch(header)\n', '    match = _RANGE.fullmatch(header.split(",")[0])\n')],
    '[꼴] 앞뒤 공백을 걷어냄': [('    match = _RANGE.fullmatch(header)\n', '    match = _RANGE.fullmatch(header.strip())\n')],
    '[꼴] 단위를 묻지 않음': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"[a-z]+=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] 부호 붙은 시작을 받음': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=(\\+?[0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n')],
    '[꼴] 빈 헤더는 본문 전체': [('    match = _RANGE.fullmatch(header)\n', '    if not header:\n        return 0, size\n    match = _RANGE.fullmatch(header)\n')],
    '[거절] 빈 본문에는 빈 값': [('    if first > last or first >= size:\n', '    if first > last or first >= size > 0:\n')],
    '[반열린] 끝 안쪽 b 에만 1 을 더하지 않음': [('    return first, min(last, size - 1) + 1\n', '    return first, size if last >= size - 1 else last\n')],
    '[반열린] 바이트 차례를 뒤집음 (억지 - 내용 축 확인용)': [('    return body[start:stop]\n', '    return body[start:stop][::-1]\n')],
    '[꼴] re.ASCII 없이 IGNORECASE - ſ 를 s 로 접어 받음 (점검 앞의 decoy)': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE)\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[-O] 범위 확인을 assert 로 - python -O 에서는 bytes=2-1 이 빈 값을 냄': [('    if first > last or first >= size:\n        raise ValueError(f"만족할 수 없는 범위: {header!r}")\n', '    assert first <= last and first < size, f"만족할 수 없는 범위: {header!r}"\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "끝을 길이로 줄임 (안전)": [(_STOP, "    return first, min(last + 1, size)\n")],
    "memoryview 로 자름 (안전)": [("    return body[start:stop]\n", "    return memoryview(body)[start:stop].tobytes()\n")],
    "도우미가 slice 를 돌려줌 (안전)": [
        ("def _byte_range(header: str, size: int) -> tuple[int, int]:\n", "def _byte_range(header: str, size: int) -> slice:\n"),
        (_STOP, "    return slice(first, min(last, size - 1) + 1)\n"),
        ("    start, stop = _byte_range(header, len(body))\n    return body[start:stop]\n", "    return body[_byte_range(header, len(body))]\n"),
    ],
    "IndexError 로 거절 (안전)": [('        raise ValueError(f"만족할 수 없는 범위: {header!r}")\n', "        raise IndexError(header)\n")],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'bytearray 로 돌려줌 (컨테이너)': [('    return body[start:stop]\n', '    return bytearray(body[start:stop])\n')],
    'memoryview 를 그대로 돌려줌 (컨테이너)': [('    return body[start:stop]\n', '    return memoryview(body)[start:stop]\n')],
    '도우미가 (시작, 길이) 를 돌려줌 (안전)': [('    return first, min(last, size - 1) + 1\n', '    return first, min(last, size - 1) + 1 - first\n'), ('    return body[start:stop]\n', '    return body[start:start + stop]\n')],
    '끝을 줄이지 않음 - 조각이 끝에서 멈춘다 (안전)': [('    return first, min(last, size - 1) + 1\n', '    return first, last + 1\n')],
    'from re import (안전 · import 꼴)': [('import re\n', 'from re import ASCII, IGNORECASE, compile\n'), ('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", IGNORECASE | ASCII)\n')],
    'LookupError 로 거절 (안전)': [('        raise ValueError(f"지원하지 않는 범위: {header!r}")\n', '        raise LookupError(header)\n')],
    'lower() 뒤 대소문자를 가리는 정규식 (안전 · ASCII 읽기)': [('_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)\n', '_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})")\n'), ('    match = _RANGE.fullmatch(header)\n', '    match = _RANGE.fullmatch(header.lower())\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
