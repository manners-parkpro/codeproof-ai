"""D145 변이 - 쓰는 단계 13개 · 쓰는 단계 점검 31개 · 독립 검토 2개 (약화 32 · 안전 14 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_ATT = "    if not 1 <= attempts <= _MAX_ATTEMPTS:\n"
_ATT_RAISE = '        raise ValueError(f"attempts 는 1 부터 {_MAX_ATTEMPTS} 까지다")\n'
_BASE = "    if not 0 < base <= _MAX_BASE:\n"
_LIST = "    return [base * 2**n for n in range(attempts)]\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[횟수] 확인 없음 (twin)": [(_ATT + _ATT_RAISE, "")],
    "[횟수] 상한 하나 더": [(_ATT, "    if not 1 <= attempts <= _MAX_ATTEMPTS + 1:\n")],
    "[횟수] 0 을 받음": [(_ATT, "    if not 0 <= attempts <= _MAX_ATTEMPTS:\n")],
    "[횟수] 상한을 넘으면 상한으로 줄임": [(_ATT + _ATT_RAISE, "    attempts = min(attempts, _MAX_ATTEMPTS)\n    if attempts < 1:\n" + _ATT_RAISE)],
    "[기준] 확인 없음": [(_BASE + '        raise ValueError(f"base 는 0 보다 크고 {_MAX_BASE} 이하다")\n', "")],
    "[기준] 비교를 거꾸로 - NaN 이 지나감": [(_BASE, "    if base <= 0 or base > _MAX_BASE:\n")],
    "[기준] 0 을 받음": [(_BASE, "    if not 0 <= base <= _MAX_BASE:\n")],
    "[기준] 상한 없음": [(_BASE, "    if not 0 < base:\n")],
    "[식] 2**(n+1)": [(_LIST, "    return [base * 2 ** (n + 1) for n in range(attempts)]\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[기준] 상한에 1e-9 여유': [('    if not 0 < base <= _MAX_BASE:\n', '    if not 0 < base <= _MAX_BASE + 1e-9:\n')],
    '[기준] float 하위 클래스를 거절': [('    if not 0 < base <= _MAX_BASE:\n', '    if type(base) not in (int, float) or not 0 < base <= _MAX_BASE:\n')],
    '[횟수] 가운데 값 하나를 거절 (표에 7 이 빠짐)': [('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    if attempts not in (1, 2, 3, 4, 5, 6, 8, 9, 10):\n')],
    '[횟수] IntEnum 이면 상한을 넘어도 받음': [('_MAX_ATTEMPTS = 10\n', 'import enum\n\n_MAX_ATTEMPTS = 10\n'), ('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    if not isinstance(attempts, enum.Enum) and not 1 <= attempts <= _MAX_ATTEMPTS:\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[횟수] 아래 끝 1 을 거절': [('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    if not 1 < attempts <= _MAX_ATTEMPTS:\n')],
    '[횟수] 위 끝 10 을 거절': [('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    if not 1 <= attempts < _MAX_ATTEMPTS:\n')],
    '[횟수] Enum 을 거절': [('_MAX_ATTEMPTS = 10\n', 'import enum\n\n_MAX_ATTEMPTS = 10\n'), ('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    if isinstance(attempts, enum.Enum) or not 1 <= attempts <= _MAX_ATTEMPTS:\n')],
    '[식] 차례를 거꾸로': [('    return [base * 2**n for n in range(attempts)]\n', '    return [base * 2**n for n in reversed(range(attempts))]\n')],
    '[기준] 아주 작은 양수를 거절 (하한 0.01)': [('    if not 0 < base <= _MAX_BASE:\n', '    if not 0.01 <= base <= _MAX_BASE:\n')],
    '[기준] 위 끝 60 을 거절': [('    if not 0 < base <= _MAX_BASE:\n', '    if not 0 < base < _MAX_BASE:\n')],
    '[기준] int base 를 거절': [('    if not 0 < base <= _MAX_BASE:\n', '    if not isinstance(base, float) or not 0 < base <= _MAX_BASE:\n')],
    '[식] 첫 대기가 절반 - 2**(n-1)': [('    return [base * 2**n for n in range(attempts)]\n', '    return [base * 2 ** (n - 1) for n in range(attempts)]\n')],
    '[횟수] 아주 큰 값만 상한으로 줄임': [('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    if attempts > 10 * _MAX_ATTEMPTS:\n        attempts = _MAX_ATTEMPTS\n    if not 1 <= attempts <= _MAX_ATTEMPTS:\n')],
    '[횟수] 정확한 int 일 때만 확인 - IntEnum · int 하위 클래스가 상한을 건너뜀': [('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    if type(attempts) is int and not 1 <= attempts <= _MAX_ATTEMPTS:\n')],
    '[기준] 무한대는 상한으로 줄임': [('_MAX_ATTEMPTS = 10\n', 'import math\n\n_MAX_ATTEMPTS = 10\n'), ('    if not 0 < base <= _MAX_BASE:\n', '    if math.isinf(base):\n        base = _MAX_BASE\n    if not 0 < base <= _MAX_BASE:\n')],
    '[기준] 상한 두 배': [('    if not 0 < base <= _MAX_BASE:\n', '    if not 0 < base <= 2 * _MAX_BASE:\n')],
    '[기준] 음수를 절댓값으로': [('    if not 0 < base <= _MAX_BASE:\n', '    base = abs(base)\n    if not 0 < base <= _MAX_BASE:\n')],
    '[기준] 기준 대신 가장 긴 대기를 확인': [('    if not 0 < base <= _MAX_BASE:\n', '    if not 0 < base * 2 ** (attempts - 1) <= _MAX_BASE * 2 ** (_MAX_ATTEMPTS - 1):\n')],
    '[기준] 상한을 가장 긴 대기의 상한으로 착각': [('    if not 0 < base <= _MAX_BASE:\n', '    if not 0 < base <= _MAX_BASE * 2 ** (attempts - 1):\n')],
    '[bool] attempts 의 bool 확인 없음 (점검 앞의 decoy)': [('    if isinstance(attempts, bool):\n        raise TypeError("attempts 는 bool 이 아닌 정수다")\n', '')],
    '[bool] False 만 거절 - True 는 1회로 받음': [('    if isinstance(attempts, bool):\n', '    if attempts is False:\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[-O] attempts 범위 확인을 assert 로 - python -O 에서는 1000번짜리 목록이 나옴': [('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n        raise ValueError(f"attempts 는 1 부터 {_MAX_ATTEMPTS} 까지다")\n', '    assert 1 <= attempts <= _MAX_ATTEMPTS, f"attempts 는 1 부터 {_MAX_ATTEMPTS} 까지다"\n')],
    '[-O] base 범위 확인을 assert 로': [('    if not 0 < base <= _MAX_BASE:\n        raise ValueError(f"base 는 0 보다 크고 {_MAX_BASE} 이하다")\n', '    assert 0 < base <= _MAX_BASE, f"base 는 0 보다 크고 {_MAX_BASE} 이하다"\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "ldexp 로 (안전)": [(_LIST, "    return [math.ldexp(base, n) for n in range(attempts)]\n"), ("_MAX_ATTEMPTS = 10\n", "import math\n\n_MAX_ATTEMPTS = 10\n")],
    "두 배씩 쌓음 (안전)": [(_LIST, "    out, delay = [], base\n    for _ in range(attempts):\n        out.append(delay)\n        delay *= 2\n    return out\n")],
    "range 에 드는지로 확인 (안전)": [(_ATT, "    if attempts not in range(1, _MAX_ATTEMPTS + 1):\n")],
    "TypeError 로 거절 (안전)": [(_ATT_RAISE, "        raise TypeError(attempts)\n")],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '검사 순서를 바꿈 (안전)': [('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n        raise ValueError(f"attempts 는 1 부터 {_MAX_ATTEMPTS} 까지다")\n    if not 0 < base <= _MAX_BASE:\n        raise ValueError(f"base 는 0 보다 크고 {_MAX_BASE} 이하다")\n', '    if not 0 < base <= _MAX_BASE:\n        raise ValueError(f"base 는 0 보다 크고 {_MAX_BASE} 이하다")\n    if not 1 <= attempts <= _MAX_ATTEMPTS:\n        raise ValueError(f"attempts 는 1 부터 {_MAX_ATTEMPTS} 까지다")\n')],
    'operator.index 로 횟수를 int 로 (안전)': [('_MAX_ATTEMPTS = 10\n', 'import operator\n\n_MAX_ATTEMPTS = 10\n'), ('    if not 1 <= attempts <= _MAX_ATTEMPTS:\n', '    attempts = operator.index(attempts)\n    if not 1 <= attempts <= _MAX_ATTEMPTS:\n')],
    'isfinite 로 먼저 거름 (안전)': [('_MAX_ATTEMPTS = 10\n', 'import math\n\n_MAX_ATTEMPTS = 10\n'), ('    if not 0 < base <= _MAX_BASE:\n', '    if not math.isfinite(base) or not 0 < base <= _MAX_BASE:\n')],
    '1 << n 으로 (안전)': [('    return [base * 2**n for n in range(attempts)]\n', '    return [base * (1 << n) for n in range(attempts)]\n')],
    'base 를 float 로 바꿔 계산 (안전)': [('    return [base * 2**n for n in range(attempts)]\n', '    return [float(base) * 2**n for n in range(attempts)]\n')],
    'ArithmeticError 로 거절 (안전)': [('        raise ValueError(f"base 는 0 보다 크고 {_MAX_BASE} 이하다")\n', '        raise ArithmeticError(base)\n')],
    'from math import ldexp (안전 · import 꼴)': [('_MAX_ATTEMPTS = 10\n', 'from math import ldexp\n\n_MAX_ATTEMPTS = 10\n'), ('    return [base * 2**n for n in range(attempts)]\n', '    return [ldexp(base, n) for n in range(attempts)]\n')],
    '제너레이터를 list() 로 (안전)': [('    return [base * 2**n for n in range(attempts)]\n', '    return list(base * 2**n for n in range(attempts))\n')],
    '_MAX_BASE 를 int 60 으로 (안전)': [('_MAX_BASE = 60.0\n', '_MAX_BASE = 60\n')],
    '[bool] bool 거절을 ValueError 로 (안전)': [('        raise TypeError("attempts 는 bool 이 아닌 정수다")\n', '        raise ValueError("bool 횟수")\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
