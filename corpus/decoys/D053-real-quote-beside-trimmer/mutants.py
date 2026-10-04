"""D053 변이 - 독립 검토 · 고치기 전 판 8개 (약화 6 · 안전 2 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] binary 는 공백이 있을 때만 감쌈': [('    return " ".join([quote_arg(binary), *(quote_arg(a) for a in args)])\n', '    return " ".join([quote_arg(binary) if any(c.isspace() for c in binary) else binary, *(quote_arg(a) for a in args)])\n')],
    '[독립 검토] binary 를 감싸지 않음': [('    return " ".join([quote_arg(binary), *(quote_arg(a) for a in args)])\n', '    return " ".join([binary, *(quote_arg(a) for a in args)])\n')],
    '[독립 검토] 큰따옴표로 감쌈 ($ · 백틱이 산다)': [('    quoted = shlex.quote(value)\n    return quoted if quoted.startswith("\'") else f"\'{value}\'"\n', '    return \'"\' + value.replace(\'"\', \'\\\\"\') + \'"\'\n')],
    '[독립 검토] 공백이 있을 때만 감쌈': [('    quoted = shlex.quote(value)\n    return quoted if quoted.startswith("\'") else f"\'{value}\'"\n', '    return shlex.quote(value) if any(c.isspace() for c in value) else value\n')],
    '[독립 검토 · 고친 뒤 약화] shlex.join (= 꼴 낱말을 감싸지 않는다)': [('    return " ".join([quote_arg(binary), *(quote_arg(a) for a in args)])\n', '    return shlex.join([binary, *args])\n')],
    '[고치기 전 판] shlex.quote 만 (= 꼴 낱말을 감싸지 않는다)': [('    quoted = shlex.quote(value)\n    return quoted if quoted.startswith("\'") else f"\'{value}\'"\n', '    return shlex.quote(value)\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] 언제나 작은따옴표로 직접 감쌈': [('    quoted = shlex.quote(value)\n    return quoted if quoted.startswith("\'") else f"\'{value}\'"\n', '    return "\'" + value.replace("\'", "\'\\"\'\\"\'") + "\'"\n')],
    '[쓰는 단계] 낱말마다 map 으로 감쌈': [('    return " ".join([quote_arg(binary), *(quote_arg(a) for a in args)])\n', '    return " ".join(map(quote_arg, [binary, *args]))\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
}
