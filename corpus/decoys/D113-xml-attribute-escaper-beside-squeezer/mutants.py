"""D113 변이 - 쓰는 단계 12개 · 검토 5개 (약화 14 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[이스케이프] 감싸기만 (twin)': [
        ('    return quoteattr(value)\n', '    return f\'"{value}"\'\n'),
    ],
    '[큰따옴표] escape 에 공백 참조만 더함': [
        ('    return quoteattr(value)\n', '    from xml.sax.saxutils import escape\n    out = escape(value, {\'\\n\': \'&#10;\', \'\\t\': \'&#9;\', \'\\r\': \'&#13;\'})\n    return f\'"{out}"\'\n'),
    ],
    '[공백 문자] html.escape 로 따옴표까지 (줄바꿈은 그대로)': [
        ('    return quoteattr(value)\n', '    import html\n    return f\'"{html.escape(value)}"\'\n'),
    ],
    '[앰퍼샌드 순서] 꺾쇠 다음에 앰퍼샌드': [
        ('    return quoteattr(value)\n', '    out = value.replace(\'<\', \'&lt;\').replace(\'>\', \'&gt;\').replace(\'"\', \'&quot;\').replace(\'&\', \'&amp;\')\n    out = out.replace(\'\\n\', \'&#10;\').replace(\'\\t\', \'&#9;\').replace(\'\\r\', \'&#13;\')\n    return f\'"{out}"\'\n'),
    ],
    '[이스케이프 문자 자신] 앰퍼샌드를 빼먹음': [
        ('    return quoteattr(value)\n', '    out = value.replace(\'<\', \'&lt;\').replace(\'>\', \'&gt;\').replace(\'"\', \'&quot;\')\n    out = out.replace(\'\\n\', \'&#10;\').replace(\'\\t\', \'&#9;\').replace(\'\\r\', \'&#13;\')\n    return f\'"{out}"\'\n'),
    ],
    '[모든 칸] 제목만 확인': [
        ('    if _NOT_XML.search(sku) or _NOT_XML.search(title):\n', '    if _NOT_XML.search(title):\n'),
    ],
    '[XML 밖 문자] NUL 만 거절': [
        ('_NOT_XML = re.compile(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\ud800-\\udfff\\ufffe\\uffff]")\n', '_NOT_XML = re.compile(r"\\x00")\n'),
    ],
    '[홑 대리 문자] 제어 문자만 거절': [
        ('_NOT_XML = re.compile(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\ud800-\\udfff\\ufffe\\uffff]")\n', '_NOT_XML = re.compile(r"[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]")\n'),
    ],
    '[구간 전체] 폼 피드를 빼먹은 문자 클래스': [
        ('\\x0b\\x0c\\x0e', '\\x0b\\x0e'),
    ],
    '[검토] Y1 폼 피드를 빼먹은 문자 클래스': [
        ('\\x0b\\x0c\\x0e', '\\x0b\\x0e'),
    ],
    '[검토] Y2 구간 끝을 \\x07 로': [
        ('\\x00-\\x08', '\\x00-\\x07'),
    ],
    '[검토] Y3 구간 시작을 \\x0f 로': [
        ('\\x0e-\\x1f', '\\x0f-\\x1f'),
    ],
    '[검토] Y4 거절 대신 지움': [
        ('    if _NOT_XML.search(sku) or _NOT_XML.search(title):\n        raise ValueError("XML 에 쓸 수 없는 문자가 있다")\n', '    sku, title = _NOT_XML.sub("", sku), _NOT_XML.sub("", title)\n'),
    ],
    '[검토] Y5 거절 대신 대체 문자로': [
        ('    if _NOT_XML.search(sku) or _NOT_XML.search(title):\n        raise ValueError("XML 에 쓸 수 없는 문자가 있다")\n', '    sku, title = _NOT_XML.sub(chr(0xFFFD), sku), _NOT_XML.sub(chr(0xFFFD), title)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'ElementTree 로 직렬화 (안전)': [
        ('    return f"<item sku={_attr(sku)} title={_attr(_squeeze(title))}/>"\n', '    import xml.etree.ElementTree as ET\n    return ET.tostring(ET.Element("item", sku=sku, title=_squeeze(title)), encoding="unicode")\n'),
    ],
    'quoteattr 에 대체표를 더함 (안전)': [
        ('    return quoteattr(value)\n', '    return quoteattr(value, {"\'": \'&apos;\'})\n'),
    ],
    '다른 예외로 거절 (안전)': [
        ('        raise ValueError("XML 에 쓸 수 없는 문자가 있다")\n', '        raise TypeError(sku)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
