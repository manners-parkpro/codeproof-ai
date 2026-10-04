"""D134 변이 - 쓰는 단계 14개 · 쓰는 단계 점검 18개 (약화 23 · 안전 9 · 경쟁 0) - 쓰는 단계의 안전 하나를 약화로 옮김. 규약은 src/codeproof_ai/corpus/mutants.py."""

_FIELDS = '_FIELDS = {"name": slice(0, 20), "age": slice(20, 23), "city": slice(23, 40)}\n'
_CHECK = "    if len(line) != _WIDTH:\n"
_RETURN = '    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[경계] 열 번호를 그대로 경계로 (twin)": [(_FIELDS, '_FIELDS = {"name": slice(1, 20), "age": slice(21, 23), "city": slice(24, 40)}\n')],
    "[경계] 나이 끝을 하나 덜 - 끝 열을 뺌": [(_FIELDS, '_FIELDS = {"name": slice(0, 20), "age": slice(20, 22), "city": slice(23, 40)}\n')],
    "[경계] 도시 끝을 하나 덜": [(_FIELDS, '_FIELDS = {"name": slice(0, 20), "age": slice(20, 23), "city": slice(23, 39)}\n')],
    "[겹침] 이름이 나이 첫 열까지": [(_FIELDS, '_FIELDS = {"name": slice(0, 21), "age": slice(20, 23), "city": slice(23, 40)}\n')],
    "[지우기] 모든 공백류를 지움": [(_RETURN, "    return {field: line[span].rstrip() for field, span in _FIELDS.items()}\n")],
    "[지우기] 앞 공백도 지움": [(_RETURN, '    return {field: line[span].strip(" ") for field, span in _FIELDS.items()}\n')],
    "[길이] 긴 줄을 받음": [(_CHECK, "    if len(line) < _WIDTH:\n")],
    "[길이] 확인 없음": [(_CHECK + '        raise ValueError(f"행 길이는 {_WIDTH} 이다: {len(line)}")\n', "")],
    "[길이] 41 글자": [("_WIDTH = 40\n", "_WIDTH = 41\n")],
    # 쓰는 단계에서 「안전」으로 적었으나 주장 오라클이 잡은 약화 - $ 는 마지막 줄바꿈 앞에서도 맞는다
    "[지우기] 끝 공백을 $ 정규식으로 - 「공백 + 줄바꿈」의 공백을 지움": [
        (_RETURN, '    return {field: re.sub(" +$", "", line[span]) for field, span in _FIELDS.items()}\n'),
        ("# 명세:", "import re\n\n# 명세:"),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[지우기] 끝의 NUL 채움도 지움': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return {field: line[span].rstrip(" \\x00") for field, span in _FIELDS.items()}\n')],
    '[지우기] 끝의 전각 공백(U+3000)도 지움': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return {field: line[span].rstrip(" \\u3000") for field, span in _FIELDS.items()}\n')],
    '[지우기] 끝의 NBSP(U+00A0)도 지움': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return {field: line[span].rstrip(" \\xa0") for field, span in _FIELDS.items()}\n')],
    '[지우기] 끝의 CR 도 지움': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return {field: line[span].rstrip(" \\r") for field, span in _FIELDS.items()}\n')],
    '[지우기] 끝의 - 채움도 지움': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return {field: line[span].rstrip(" -") for field, span in _FIELDS.items()}\n')],
    '[길이] CRLF 를 떼고 잼 - 42글자 줄을 받음': [('    if len(line) != _WIDTH:\n', '    line = line.removesuffix("\\r\\n")\n    if len(line) != _WIDTH:\n')],
    '[길이] BOM 을 떼고 잼 - 41글자 줄을 받음': [('    if len(line) != _WIDTH:\n', '    line = line.removeprefix("\\ufeff")\n    if len(line) != _WIDTH:\n')],
    '[하위 타입] type(line) is str 만 받음': [('    if len(line) != _WIDTH:\n', '    if type(line) is not str or len(line) != _WIDTH:\n')],
    '[표현] NFC 로 바꾼 뒤 잼 - 결합 글자가 든 40글자 줄': [('    if len(line) != _WIDTH:\n', '    line = unicodedata.normalize("NFC", line)\n    if len(line) != _WIDTH:\n'), ('# 명세:', 'import unicodedata\n\n# 명세:')],
    '[표현] UTF-8 로 쓸 수 있는지 확인 - 짝 없는 서로게이트를 거절': [('    if len(line) != _WIDTH:\n', '    line.encode("utf-8")\n    if len(line) != _WIDTH:\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[지우기] 칸 앞의 0 채움도 지움': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return {field: line[span].rstrip(" ").lstrip("0") for field, span in _FIELDS.items()}\n')],
    '[길이] 짧은 줄을 받음': [('    if len(line) != _WIDTH:\n', '    if len(line) > _WIDTH:\n')],
    '[거절] 인쇄할 수 없는 글자가 든 줄을 거절': [('    if len(line) != _WIDTH:\n', '    if not line.isprintable():\n        raise ValueError("인쇄할 수 없는 글자")\n    if len(line) != _WIDTH:\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "칸마다 조각을 직접 씀 (안전)": [
        (_RETURN, '    return {"name": line[0:20].rstrip(" "), "age": line[20:23].rstrip(" "), "city": line[23:40].rstrip(" ")}\n'),
    ],
    "표를 (이름, 시작, 끝) 튜플로 (안전)": [
        (_FIELDS, '_FIELDS = (("name", 0, 20), ("age", 20, 23), ("city", 23, 40))\n'),
        (_RETURN, '    return {field: line[start:stop].rstrip(" ") for field, start, stop in _FIELDS}\n'),
    ],
    "거절을 TypeError 로 (안전)": [
        ('        raise ValueError(f"행 길이는 {_WIDTH} 이다: {len(line)}")\n', "        raise TypeError(len(line))\n"),
    ],
    "끝 공백을 \\Z 정규식으로 지움 (안전)": [
        (_RETURN, '    return {field: re.sub(" +\\\\Z", "", line[span]) for field, span in _FIELDS.items()}\n'),
        ("# 명세:", "import re\n\n# 명세:"),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '표를 명세의 1부터 센 포함 구간으로 두고 조각을 계산 (안전)': [('_FIELDS = {"name": slice(0, 20), "age": slice(20, 23), "city": slice(23, 40)}\n', '_FIELDS = {"name": (1, 20), "age": (21, 23), "city": (24, 40)}\n'), ('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return {field: line[first - 1:last].rstrip(" ") for field, (first, last) in _FIELDS.items()}\n')],
    '끝 공백을 while 로 하나씩 지움 (안전)': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    out = {}\n    for field, span in _FIELDS.items():\n        text = line[span]\n        while text.endswith(" "):\n            text = text[:-1]\n        out[field] = text\n    return out\n')],
    'dict(zip(...)) 로 만듦 (안전)': [('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return dict(zip(_FIELDS, (line[s].rstrip(" ") for s in _FIELDS.values())))\n')],
    '도시를 끝까지 slice(23, None) 로 (안전)': [('_FIELDS = {"name": slice(0, 20), "age": slice(20, 23), "city": slice(23, 40)}\n', '_FIELDS = {"name": slice(0, 20), "age": slice(20, 23), "city": slice(23, None)}\n')],
    'OrderedDict 로 돌려줌 - dict 하위 타입 컨테이너 (안전)': [('# 명세:', 'from collections import OrderedDict\n\n# 명세:'), ('    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}\n', '    return OrderedDict((field, line[span].rstrip(" ")) for field, span in _FIELDS.items())\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
