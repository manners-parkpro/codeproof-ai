"""D042 변이 - 독립 검토 9개 (약화 3 · 안전 2 · 경쟁 4). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] boundary lt -1': [('    if cost < 0 or _tokens["available"] < cost:\n', '    if cost < -1 or _tokens["available"] < cost:\n')],
    '[독립 검토] prefix no neg check': [('    if cost < 0 or _tokens["available"] < cost:\n', '    if _tokens["available"] < cost:\n')],
    '[독립 검토] type is int': [('    if cost < 0 or _tokens["available"] < cost:\n', '    if (type(cost) is int and cost < 0) or _tokens["available"] < cost:\n')],
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] lock class Lock': [('_lock = threading.RLock()\n', '_lock = threading.Lock()\n')],
    '[독립 검토] neg check in take': [('    if cost < 0 or _tokens["available"] < cost:\n        return False\n    _tokens["available"] -= cost\n    return True\n\n\ndef take(cost: int = 1) -> bool:\n', '    if _tokens["available"] < cost:\n        return False\n    _tokens["available"] -= cost\n    return True\n\n\ndef take(cost: int = 1) -> bool:\n    if cost < 0:\n        return False\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] lock only for cost 1': [('    with _lock:\n        return _consume(cost)\n', '    if cost == 1:\n        with _lock:\n            return _consume(cost)\n    return _consume(cost)\n')],
    '[독립 검토] new lock per call': [('    with _lock:\n', '    with threading.RLock():\n')],
    '[독립 검토] no lock': [('    with _lock:\n        return _consume(cost)\n', '    return _consume(cost)\n')],
    '[독립 검토] semaphore 2': [('_lock = threading.RLock()\n', '_lock = threading.Semaphore(2)\n')],
}
