"""D032 변이 - 독립 검토 10개 (약화 7 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] dangerous without cr': [('_DANGEROUS = ("=", "+", "-", "@", "\\t", "\\r")\n', '_DANGEROUS = ("=", "+", "-", "@", "\\t")\n')],
    '[독립 검토] dangerous without eq': [('_DANGEROUS = ("=", "+", "-", "@", "\\t", "\\r")\n', '_DANGEROUS = ("+", "-", "@", "\\t", "\\r")\n')],
    '[독립 검토] first value only': [('    return ",".join(neutralize_cell(v) for v in values)\n', '    return ",".join([neutralize_cell(values[0]), *values[1:]]) if values else ""\n')],
    '[독립 검토] no doubling': [('        value = \'"\' + value.replace(\'"\', \'""\') + \'"\'\n', '        value = \'"\' + value + \'"\'\n')],
    '[독립 검토] no quoting prefix': [('    if any(ch in value for ch in \',"\\r\\n\'):\n        value = \'"\' + value.replace(\'"\', \'""\') + \'"\'\n', '')],
    '[독립 검토] quote only comma': [('    if any(ch in value for ch in \',"\\r\\n\'):\n', "    if ',' in value:\n")],
    '[독립 검토] trigger without dquote': [('    if any(ch in value for ch in \',"\\r\\n\'):\n', "    if any(ch in value for ch in ',\\r\\n'):\n")],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] ValueError on newline instead': [('    if any(ch in value for ch in \',"\\r\\n\'):\n', '    if any(ch in value for ch in \'\\r\\n\'):\n        raise ValueError(\'newline in cell\')\n    if any(ch in value for ch in \',"\'):\n')],
    '[독립 검토] csv writer minimal': [('\n_DANGEROUS = ("=", "+", "-", "@", "\\t", "\\r")\n\n\ndef quote_cell(value: str) -> str:\n    """표시용 따옴표 감싸기. 수식 주입 방어가 아니다."""\n    return f\'"{value}"\'\n\n\ndef neutralize_cell(value: str) -> str:\n    if value.startswith(_DANGEROUS):\n        value = "\'" + value\n    if any(ch in value for ch in \',"\\r\\n\'):\n        value = \'"\' + value.replace(\'"\', \'""\') + \'"\'\n', '\nimport csv\nimport io\n\n_DANGEROUS = ("=", "+", "-", "@", "\\t", "\\r")\n\n\ndef quote_cell(value: str) -> str:\n    """표시용 따옴표 감싸기. 수식 주입 방어가 아니다."""\n    return f\'"{value}"\'\n\n\ndef neutralize_cell(value: str) -> str:\n    if value.startswith(_DANGEROUS):\n        value = "\'" + value\n    buf = io.StringIO()\n    csv.writer(buf, lineterminator=\'\').writerow([value])\n    value = buf.getvalue()\n')],
    '[독립 검토] quote all': [('    if any(ch in value for ch in \',"\\r\\n\'):\n', '    if True:\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
