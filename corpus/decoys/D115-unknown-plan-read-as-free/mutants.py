"""D115 변이 - 쓰는 단계 9개 · 검토 3개 (약화 9 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[표 밖 이름] 그대로 돌려줌 (twin)': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS.get(plan, plan)\n'),
    ],
    '[표 밖 이름] 정규화해 찾고 없으면 원래 값': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS.get(plan.strip().lower(), plan)\n'),
    ],
    '[기본 등급] 처리하지 않는 등급을 기본값으로': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS.get(plan, "basic")\n'),
    ],
    '[표의 값 전부] 표에 처리하지 않는 등급을 더함': [
        ('_TIERS = {"free": "free", "starter": "free", "pro": "pro", "team": "pro"}\n', '_TIERS = {"free": "free", "starter": "free", "pro": "pro", "team": "pro", "vip": "vip"}\n'),
    ],
    '[접두사] 앞부분이 맞으면 그 등급': [
        ('    return _TIERS.get(plan, "free")\n', '    return next((t for k, t in _TIERS.items() if plan.startswith(k)), plan)\n'),
    ],
    '[표 밖 이름 · 한도] 정규화해 찾음 - Pro 가 pro 한도': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS.get(plan.strip().lower(), "free")\n'),
    ],
    '[표 밖 이름 · 한도] 모르는 이름을 pro 로': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS.get(plan, "pro")\n'),
    ],
    '[검토] U1 모르는 이름을 pro 로': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS.get(plan, "pro")\n'),
    ],
    '[검토] U2 정규화해 찾고 없으면 free (Pro 가 pro 한도)': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS.get(plan.strip().lower(), "free")\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '모르는 요금제는 KeyError (안전)': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS[plan]\n'),
    ],
    'match 로 두 등급 (안전)': [
        ('    return _TIERS.get(plan, "free")\n', '    match _TIERS.get(plan):\n        case "pro":\n            return "pro"\n        case _:\n            return "free"\n'),
    ],
    '[검토] U3 모르는 이름은 KeyError (안전 - 거절)': [
        ('    return _TIERS.get(plan, "free")\n', '    return _TIERS[plan]\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
