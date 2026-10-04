"""D019 변이 - 독립 검토 13개 (약화 8 · 안전 5 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] count 1': [('    return _CONTROL.sub("", text)\n', '    return _CONTROL.sub("", text, count=1)\n')],
    '[독립 검토] count 2': [('    return _CONTROL.sub("", text)\n', '    return _CONTROL.sub("", text, count=2)\n')],
    '[독립 검토] count 3': [('    return _CONTROL.sub("", text)\n', '    return _CONTROL.sub("", text, count=3)\n')],
    '[독립 검토] first 80 only': [('    return _CONTROL.sub("", text)\n', '    return _CONTROL.sub("", text[:80]) + text[80:]\n')],
    '[독립 검토] missing u2029': [('_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f-\\x9f\\u2028\\u2029]")\n', '_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f-\\x9f\\u2028]")\n')],
    '[독립 검토] no x85': [('_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f-\\x9f\\u2028\\u2029]")\n', '_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f\\u2028\\u2029]")\n')],
    '[독립 검토] original C0 only': [('_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f-\\x9f\\u2028\\u2029]")\n', '_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f]")\n')],
    '[독립 검토] range end x84': [('_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f-\\x9f\\u2028\\u2029]")\n', '_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f-\\x84\\u2028\\u2029]")\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] escape hex': [('    return _CONTROL.sub("", text)\n', '    return _CONTROL.sub(lambda m: "<%02x>" % ord(m.group()), text)\n')],
    '[독립 검토] join splitlines': [('    return _CONTROL.sub("", text)\n', '    return " ".join(text.splitlines())\n')],
    '[독립 검토] only splitlines boundaries': [('_CONTROL = re.compile(r"[\\x00-\\x1f\\x7f-\\x9f\\u2028\\u2029]")\n', '_CONTROL = re.compile(r"[\\n\\r\\x0b\\x0c\\x1c-\\x1e\\x85\\u2028\\u2029]")\n')],
    '[독립 검토] replace with space': [('    return _CONTROL.sub("", text)\n', '    return _CONTROL.sub(" ", text)\n')],
    '[독립 검토] unicodedata category': [('    return _CONTROL.sub("", text)\n', '    import unicodedata\n    return "".join(c for c in text if unicodedata.category(c) not in ("Cc", "Zl", "Zp"))\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
