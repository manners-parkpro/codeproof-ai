"""D141 변이 - 쓰는 단계 12개 · 쓰는 단계 점검 27개 · 독립 검토 3개 (약화 27 · 안전 15 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_PAGE = "{_script_json(state)}"
_ESC = '    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n'
_DUMP = '    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[이웃] 이스케이프 없는 _compact_json 을 부름 (twin)": [(_PAGE, "{_compact_json(state)}")],
    "[이스케이프] > 만": [(_ESC, '    return text.replace(">", "\\\\u003e")\n')],
    "[이스케이프] HTML 참조로 - script 의 글은 원문이라 값이 바뀜": [(_ESC, "    return html.escape(text, quote=False)\n"), ("import json\n", "import html\nimport json\n")],
    "[이스케이프] 소문자 </script 만": [(_ESC, '    return text.replace("</script", "<\\\\/script")\n')],
    "[이스케이프] & 를 \\u0026 대신 &amp; 로": [(_ESC, '    return text.replace("&", "&amp;").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n')],
    "[차례] 이스케이프를 dumps 앞 값에 - 키는 그대로": [
        (_DUMP + _ESC, "    if isinstance(value, str):\n        value = value.replace(\"<\", \"\")\n    return json.dumps(value, separators=(\",\", \":\"), allow_nan=False)\n"),
    ],
    "[구조] id 를 빠뜨림": [('<script type="application/json" id="state">', '<script type="application/json">')],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[이스케이프] 공백 · > 로 끝나는 </script 만 (대소문자 무시) - / 로 끝나는 닫는 태그는 그대로': [('    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n', '    return re.sub(r"(?i)</script(?=[\\s>])", lambda m: "\\\\u003c" + m.group()[1:], text)\n'), ('import json\n', 'import json\nimport re\n')],
    '[하위 타입] 문자열 상태를 str() 로 평범한 str 로 - (str, Enum) 은 이름이 된다': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    if isinstance(value, str):\n        value = str(value)\n    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[이스케이프] JSON 의 \\t 를 실제 탭으로 되돌림 - 엄격한 JSON 이 아니다': [('    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n', '    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e").replace("\\\\t", "\\t")\n')],
    '[이스케이프] <!-- 를 JS 식 <\\!-- 로 - JSON 에 없는 이스케이프': [('    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n', '    return text.replace("<!--", "<\\\\!--").replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n')],
    '(인위적) [값] 한 글자 문자열 상태만 HTML 참조로 바꿈': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    if isinstance(value, str) and len(value) == 1:\n        return html.escape(json.dumps(value), quote=False)\n    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n'), ('import json\n', 'import html\nimport json\n')],
    '[이스케이프] dumps 결과의 HTML 참조를 먼저 풂 (이중 해석)': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = html.unescape(json.dumps(value, separators=(",", ":"), allow_nan=False))\n'), ('import json\n', 'import html\nimport json\n')],
    '[이스케이프] 겹친 역슬래시를 하나로 (이중 이스케이프를 되돌림)': [('    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n', '    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e").replace("\\\\\\\\u", "\\\\u")\n')],
    '[값] 빈 · 거짓 상태를 {} 로 (value or {})': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = json.dumps(value or {}, separators=(",", ":"))\n')],
    '[차례] 최상위 문자열은 이스케이프 없이 dumps': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    if isinstance(value, str):\n        return json.dumps(value)\n    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n')],
    '[차례] 손으로 짠 dict 직렬화가 문자열 값만 이스케이프 - 목록 값은 그대로': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    if isinstance(value, dict):\n        return "{" + ",".join(f"{_script_json(str(k))}:{_script_json(v) if isinstance(v, str) else json.dumps(v)}" for k, v in value.items()) + "}"\n    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n')],
    '[차례] 손으로 짠 dict 직렬화가 값만 이스케이프 - 키는 그대로': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    if isinstance(value, dict):\n        return "{" + ",".join(f"{json.dumps(str(k))}:{_script_json(v)}" for k, v in value.items()) + "}"\n    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n')],
    '[이웃] 목록 상태만 _compact_json 으로': [('{_script_json(state)}', '{(_compact_json if isinstance(state, list) else _script_json)(state)}')],
    '[값] 손으로 짠 dict 직렬화가 키를 문자열로 바꾸지 않음 - int 키가 맨 숫자로 나간다': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    if isinstance(value, dict):\n        return "{" + ",".join(f"{_script_json(k)}:{_script_json(v)}" for k, v in value.items()) + "}"\n    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n')],
    '[구조] 데이터 블록 뒤에 실행 script 요소를 덧붙임': [("}</script>'", "}</script><script>hydrate()</script>'")],
    '[구조] 스스로 닫는 <script/> 뒤 주석에 JSON 을 넣음': [('id="state">{_script_json(state)}</script>', 'id="state"/><!--{_script_json(state)}--></script>')],
    '[덧붙은 속성] nonce 를 더함 - 주장은 다른 속성이 없다고 말한다': [('<script type="application/json" id="state">', '<script type="application/json" id="state" nonce="r4nd">')],
    '[값] allow_nan 기본값 - NaN · Infinity 를 그대로 냄 (점검 앞의 decoy)': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = json.dumps(value, separators=(",", ":"))\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[거절] 쓸 수 없는 값은 str() 로 - default=str (집합 · 날짜 · bytes 가 글이 됨)': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = json.dumps(value, separators=(",", ":"), allow_nan=False, default=str)\n')],
    '[거절] 쓸 수 없는 키는 건너뜀 - skipkeys=True (튜플 키 항목이 사라짐)': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = json.dumps(value, separators=(",", ":"), allow_nan=False, skipkeys=True)\n')],
    '[거절] 쓸 수 없는 값은 list() 로 - default=list (집합 · bytes 가 배열이 됨)': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = json.dumps(value, separators=(",", ":"), allow_nan=False, default=list)\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "< 만 이스케이프 (안전)": [(_ESC, '    return text.replace("<", "\\\\u003c")\n')],
    "ensure_ascii=False (안전)": [(_DUMP, '    text = json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False)\n')],
    "기본 구분자 (안전)": [(_DUMP, "    text = json.dumps(value, allow_nan=False)\n")],
    "translate 로 한 번에 (안전)": [
        (_ESC, '    return text.translate({ord("&"): "\\\\u0026", ord("<"): "\\\\u003c", ord(">"): "\\\\u003e"})\n'),
    ],
    "정규식으로 바꿈 (안전)": [
        (_ESC, '    return re.sub("[&<>]", lambda m: f"\\\\u{ord(m.group()):04x}", text)\n'),
        ("import json\n", "import json\nimport re\n"),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '[속성 순서] id 를 type 앞에 (안전)': [('<script type="application/json" id="state">', '<script id="state" type="application/json">')],
    '[따옴표] 속성을 작은따옴표로 (안전)': [('<script type="application/json" id="state">', "<script type=\\'application/json\\' id=\\'state\\'>")],
    '[대문자 태그] <SCRIPT ...></SCRIPT> (안전)': [('<script type="application/json" id="state">', '<SCRIPT type="application/json" id="state">'), ("}</script>'", "}</SCRIPT>'")],
    '[이스케이프] / 도 \\/ 로 (안전)': [('    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n', '    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e").replace("/", "\\\\/")\n')],
    '[이스케이프] 대문자 16진 \\u003C \\u003E (안전)': [('    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n', '    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003C").replace(">", "\\\\u003E")\n')],
    '[import 꼴] from json import dumps as _dumps (안전)': [('import json\n', 'import json\nfrom json import dumps as _dumps\n'), ('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = _dumps(value, separators=(",", ":"), allow_nan=False)\n')],
    '[예외 타입] 쓸 수 없는 상태는 ValueError 로 (안전)': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    try:\n        text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n    except TypeError as exc:\n        raise ValueError(str(exc)) from exc\n')],
    '[구현] JSONEncoder.encode (안전)': [('    text = json.dumps(value, separators=(",", ":"), allow_nan=False)\n', '    text = json.JSONEncoder(separators=(",", ":"), allow_nan=False).encode(value)\n')],
    '[이스케이프] < 뒤에 / 나 ! 가 올 때만 (안전)': [('    return text.replace("&", "\\\\u0026").replace("<", "\\\\u003c").replace(">", "\\\\u003e")\n', '    return text.replace("</", "\\\\u003c/").replace("<!", "\\\\u003c!")\n')],
    '[감싸기] JSON 앞뒤에 줄바꿈 (안전)': [('id="state">{_script_json(state)}</script>', 'id="state">\\n{_script_json(state)}\\n</script>')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
