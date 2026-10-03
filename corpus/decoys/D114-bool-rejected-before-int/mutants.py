"""D114 변이 - 쓰는 단계 9개 · 검토 3개 (약화 10 · 안전 2 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[bool] 확인 없음 (twin)': [
        ('    if isinstance(amount, bool):\n        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n', ''),
    ],
    '[거짓] True 만 거름': [
        ('    if isinstance(amount, bool):\n', '    if amount is True:\n'),
    ],
    '[참] False 만 거름': [
        ('    if isinstance(amount, bool):\n', '    if amount is False:\n'),
    ],
    '[순서] 정수 분기 뒤에서 거름': [
        ('    if isinstance(amount, bool):\n        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n    if isinstance(amount, int):\n        return amount * 100\n', '    if isinstance(amount, int):\n        return amount * 100\n    if isinstance(amount, bool):\n        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n'),
    ],
    '[정수 0 · 1] 값으로 비교해 거름': [
        ('    if isinstance(amount, bool):\n', '    if amount in (True, False):\n'),
    ],
    '[int 하위 클래스] 정수 분기를 type is int 로': [
        ('    if isinstance(amount, bool):\n        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n    if isinstance(amount, int):\n        return amount * 100\n', '    if type(amount) is int:\n        return amount * 100\n'),
    ],
    '[float 로 틀리는 금액] float 로 계산': [
        ('    units, _, cents = amount.partition(".")\n    return int(units) * 100 + int(cents.ljust(2, "0"))\n', '    return int(float(amount) * 100)\n'),
    ],
    '[검토] Z1 정수 분기를 type is int 로 (int 하위 클래스를 떨어뜨림)': [
        ('    if isinstance(amount, bool):\n        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n    if isinstance(amount, int):\n        return amount * 100\n', '    if type(amount) is int:\n        return amount * 100\n'),
    ],
    '[검토] Z2 float 로 계산': [
        ('    units, _, cents = amount.partition(".")\n    return int(units) * 100 + int(cents.ljust(2, "0"))\n', '    return int(float(amount) * 100)\n'),
    ],
    '[검토] Z3 float 로 계산해 반올림': [
        ('    units, _, cents = amount.partition(".")\n    return int(units) * 100 + int(cents.ljust(2, "0"))\n', '    return round(float(amount) * 100)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'type is bool (안전)': [
        ('    if isinstance(amount, bool):\n', '    if type(amount) is bool:\n'),
    ],
    '다른 예외로 거절 (안전)': [
        ('        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")\n', '        raise ValueError(amount)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
