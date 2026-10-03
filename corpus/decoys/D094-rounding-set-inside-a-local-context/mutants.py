"""D094 변이 - 쓰는 단계 5개 · 검토 0개 (약화 4 · 안전 1 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '사본 없이 현재 문맥 (twin 꼴)': [
        ('    with decimal.localcontext() as ctx:\n        yield ctx\n', '    yield decimal.getcontext()\n'),
    ],
    '저장 · 복원을 finally 없이': [
        ('    with decimal.localcontext() as ctx:\n        yield ctx\n', '    saved = decimal.getcontext().copy()\n    yield decimal.getcontext()\n    decimal.setcontext(saved)\n'),
    ],
    '새 문맥을 세우고 되돌리지 않음': [
        ('    with decimal.localcontext() as ctx:\n        yield ctx\n', '    ctx = decimal.getcontext().copy()\n    decimal.setcontext(ctx)\n    yield ctx\n'),
    ],
    '기본값으로 되돌림': [
        ('    with decimal.localcontext() as ctx:\n        yield ctx\n', '    ctx = decimal.getcontext()\n    try:\n        yield ctx\n    finally:\n        ctx.prec = 28\n        ctx.rounding = decimal.ROUND_HALF_EVEN\n        ctx.clear_flags()\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '저장 · 복원을 finally 로 (안전)': [
        ('    with decimal.localcontext() as ctx:\n        yield ctx\n', '    saved = decimal.getcontext()\n    ctx = saved.copy()\n    decimal.setcontext(ctx)\n    try:\n        yield ctx\n    finally:\n        decimal.setcontext(saved)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
