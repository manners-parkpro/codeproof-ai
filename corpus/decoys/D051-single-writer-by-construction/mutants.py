"""D051 변이 - 독립 검토 7개 (약화 0 · 안전 2 · 경쟁 5). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
}
SAFE: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] RLock': [('_run_lock = threading.Lock()\n', '_run_lock = threading.RLock()\n')],
    '[독립 검토] lock in drain': [('    for value in values:\n        _accumulate(value)\n\n\ndef run(values: list[int]) -> int:\n    with _run_lock:\n        workers = [threading.Thread(target=_drain, args=(values,))]\n        for worker in workers:\n            worker.start()\n        for worker in workers:\n            worker.join()\n        return _totals["sum"]\n', '    with _run_lock:\n        for value in values:\n            _accumulate(value)\n\n\ndef run(values: list[int]) -> int:\n    workers = [threading.Thread(target=_drain, args=(values,))]\n    for worker in workers:\n        worker.start()\n    for worker in workers:\n        worker.join()\n    return _totals["sum"]\n')],
}
RACY: dict[str, list[tuple[str, str]]] = {
    '[독립 검토] lock per call': [('    with _run_lock:\n', '    with threading.Lock():\n')],
    '[독립 검토] lock released before join': [('        for worker in workers:\n            worker.join()\n        return _totals["sum"]\n', '    for worker in workers:\n        worker.join()\n    return _totals["sum"]\n')],
    '[독립 검토] no run lock': [('    with _run_lock:\n        workers = [threading.Thread(target=_drain, args=(values,))]\n        for worker in workers:\n            worker.start()\n        for worker in workers:\n            worker.join()\n        return _totals["sum"]\n', '    workers = [threading.Thread(target=_drain, args=(values,))]\n    for worker in workers:\n        worker.start()\n    for worker in workers:\n        worker.join()\n    return _totals["sum"]\n')],
    '[독립 검토] semaphore 2': [('_run_lock = threading.Lock()\n', '_run_lock = threading.Semaphore(2)\n')],
    '[독립 검토] skip lock small lists': [('def run(values: list[int]) -> int:\n    with _run_lock:\n', 'def run(values: list[int]) -> int:\n    if len(values) < 500:\n        workers = [threading.Thread(target=_drain, args=(values,))]\n        for worker in workers:\n            worker.start()\n        for worker in workers:\n            worker.join()\n        return _totals["sum"]\n    with _run_lock:\n')],
}
