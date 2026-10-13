"""주장 축별 변이 - 부호, 크기, 하위 타입, 문자열 경계와 실행 시점의 비트 불변식을 검사한다."""

GUARD = "    flags = flags & ~LEGACY_EXPRESSION"

CLAIM_AXES = {
    "부호": ("음수 옵션", "negative-options-skipped", "reject-negative-valueerror"),
    "크기": ("64비트 밖 양수와 음수", "large-positive-options-skipped", "modulo-normalization"),
    "정수 하위 타입": ("PlainInt와 IntEnum", "plain-subtypes-skipped", "commuted-mask"),
    "다른 옵션 조합": ("129와 -1", "combined-options-skipped", "arithmetic-bit-removal"),
    "빈 문자열": ("빈 str", "empty-text-skipped", "remove-obsolete-branch"),
    "문자열 크기": ("4095, 4096, 4097자", "long-text-skipped", "augmented-assignment"),
    "문자열 하위 타입": ("PlainText와 str Enum", "text-subtypes-skipped", "renamed-evaluator-import"),
    "문자 내용": ("비ASCII와 NUL과 서로게이트", "non-ascii-text-skipped", "unrelated-rendering-change"),
    "실행 모드": ("일반 실행과 -O", "assert-only", "reject-negative-overflowerror"),
    "분기 시점": ("가드 뒤 입력 복원", "restored-after-normalization", "different-option-bit"),
}

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "positive-option-bypass": [
        (GUARD, "    flags = flags")
    ],
    "wrong-bit-cleared": [
        (GUARD, "    flags = flags & ~UPPERCASE")
    ],
    "negative-options-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if flags >= 0 else flags")
    ],
    "large-positive-options-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if flags < (1 << 64) else flags")
    ],
    "large-negative-options-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if flags >= -(1 << 64) else flags")
    ],
    "plain-subtypes-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if type(flags) is int else flags")
    ],
    "combined-options-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if flags == LEGACY_EXPRESSION else flags")
    ],
    "empty-text-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if text else flags")
    ],
    "long-text-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if len(text) < 4096 else flags")
    ],
    "text-subtypes-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if type(text) is str else flags")
    ],
    "non-ascii-text-skipped": [
        (GUARD, "    flags = flags & ~LEGACY_EXPRESSION if text.isascii() else flags")
    ],
    "subtraction-enables-cleared-bit": [
        (GUARD, "    flags = flags - LEGACY_EXPRESSION")
    ],
    "toggle-enables-cleared-bit": [
        (GUARD, "    flags = flags ^ LEGACY_EXPRESSION")
    ],
    "assert-only": [
        (GUARD, "    assert not flags & LEGACY_EXPRESSION")
    ],
    "restored-after-normalization": [
        (GUARD, "    original = flags\n" + GUARD + "\n    flags = original")
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "commuted-mask": [
        (GUARD, "    flags = ~LEGACY_EXPRESSION & flags")
    ],
    "arithmetic-bit-removal": [
        (GUARD, "    flags = flags - (flags & LEGACY_EXPRESSION)")
    ],
    "modulo-normalization": [
        (GUARD, "    flags = flags % LEGACY_EXPRESSION")
    ],
    "augmented-assignment": [
        (GUARD, "    flags &= ~LEGACY_EXPRESSION")
    ],
    "different-option-bit": [
        ("LEGACY_EXPRESSION = 128", "LEGACY_EXPRESSION = 256")
    ],
    "renamed-evaluator-import": [
        ("UPPERCASE = 1", "from builtins import eval as evaluate\n\nUPPERCASE = 1"),
        ("str(eval(text))", "str(evaluate(text))")
    ],
    "reject-negative-valueerror": [
        (GUARD, "    if flags < 0:\n        raise ValueError(flags)\n" + GUARD)
    ],
    "reject-negative-overflowerror": [
        (GUARD, "    if flags < 0:\n        raise OverflowError(flags)\n" + GUARD)
    ],
    "unrelated-rendering-change": [
        ("return text.upper()", "return text.lower()")
    ],
    "remove-obsolete-branch": [
        ("    if flags & LEGACY_EXPRESSION:\n        return str(eval(text))\n", "")
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
