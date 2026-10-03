"""D105 변이 - 쓰는 단계 9개 · 검토 2개 (약화 6 · 안전 5 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[표 밖 이름] 맞지 않으면 그대로 (twin)': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    return fmt\n'),
    ],
    '[대소문자] 소문자로 확인하고 원래 값을 넘김': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    if fmt.lower() in ("json", "toml"):\n        return {"json": "json", "toml": "tomllib"}.get(fmt, fmt)\n    raise ValueError(fmt)\n'),
    ],
    '[앞뒤 공백] strip 으로 확인하고 원래 값을 넘김': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    if fmt.strip() in ("json", "toml"):\n        return {"json": "json", "toml": "tomllib"}.get(fmt, fmt)\n    raise ValueError(fmt)\n'),
    ],
    '[하위 모듈] 앞부분만 확인': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    if fmt.split(".")[0] in ("json", "toml"):\n        return {"toml": "tomllib"}.get(fmt, fmt)\n    raise ValueError(fmt)\n'),
    ],
    '[거부 목록] 위험한 이름만 막음': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    if fmt in ("os", "subprocess", "sys", "shutil"):\n        raise ValueError(fmt)\n    return {"toml": "tomllib"}.get(fmt, fmt)\n'),
    ],
    '[다른 표현] NFKC 로 확인하고 원래 값을 넘김': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    import unicodedata\n    if unicodedata.normalize("NFKC", fmt) in ("json", "toml"):\n        return {"json": "json", "toml": "tomllib"}.get(fmt, fmt)\n    raise ValueError(fmt)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '표에서 찾고 없으면 LookupError (안전)': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    return {"json": "json", "toml": "tomllib"}[fmt]\n'),
    ],
    '정규화한 값으로 match (안전)': [
        ('    match fmt:\n', '    match fmt.strip().lower():\n'),
    ],
    'if 사슬로 상수 반환 (안전)': [
        ('    match fmt:\n        case "json":\n            return "json"\n        case "toml":\n            return "tomllib"\n    raise ValueError(f"지원하지 않는 형식: {fmt!r}")\n', '    if fmt == "json":\n        return "json"\n    if fmt == "toml":\n        return "tomllib"\n    raise TypeError(fmt)\n'),
    ],
    '[검토] from importlib import import_module (안전)': [
        ('import importlib\n', 'from importlib import import_module\n'),
        ('    parser = importlib.import_module(name)\n', '    parser = import_module(name)\n'),
    ],
    '[검토] import importlib as _il (안전)': [
        ('import importlib\n', 'import importlib as _il\n'),
        ('    parser = importlib.import_module(name)\n', '    parser = _il.import_module(name)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
