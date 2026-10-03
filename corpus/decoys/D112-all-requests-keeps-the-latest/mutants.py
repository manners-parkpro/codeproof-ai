"""D112 변이 - 쓰는 단계 10개 · 검토 2개 (약화 5 · 안전 2 · 경쟁 5). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[상한] maxlen 없음 (twin)': [
        ('collections.deque(maxlen=1000)\n', 'collections.deque()\n'),
    ],
    '[상한 값] maxlen 1001': [
        ('collections.deque(maxlen=1000)\n', 'collections.deque(maxlen=1001)\n'),
    ],
    '[순서] 왼쪽으로 덧붙임': [
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    with _lock:\n        _all_requests.appendleft((time.monotonic(), path))\n'),
    ],
    '[안의 상태] 읽을 때만 자름': [
        ('collections.deque(maxlen=1000)\n', 'collections.deque()\n'),
        ('        return list(_all_requests)\n', '        return list(_all_requests)[-1000:]\n'),
    ],
    '[덜어 내는 경계] 1001개까지 남김': [
        ('collections.deque(maxlen=1000)\n', 'collections.deque()\n'),
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    with _lock:\n        _all_requests.append((time.monotonic(), path))\n        while len(_all_requests) > 1001:\n            _all_requests.popleft()\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '덧붙인 뒤 락 안에서 덜어 냄 (안전)': [
        ('collections.deque(maxlen=1000)\n', 'collections.deque()\n'),
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    with _lock:\n        _all_requests.append((time.monotonic(), path))\n        while len(_all_requests) > 1000:\n            _all_requests.popleft()\n'),
    ],
    '상한을 상수로 (안전)': [
        ('_lock = threading.Lock()\n', '_LIMIT = 1000\n_lock = threading.Lock()\n'),
        ('collections.deque(maxlen=1000)\n', 'collections.deque(maxlen=_LIMIT)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {
    '[여러 스레드 · 도중] 락 없이 덧붙이고 덜어 냄 - 끝 길이만 맞음': [
        ('collections.deque(maxlen=1000)\n', 'collections.deque()\n'),
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    _all_requests.append((time.monotonic(), path))\n    if len(_all_requests) > 1000:\n        _all_requests.popleft()\n'),
    ],
    '[여러 스레드] 잘라 둔 사본을 다음 줄에서 바꿔 끼움 (락 없이)': [
        ('_all_requests: collections.deque[tuple[float, str]] = collections.deque(maxlen=1000)\n', '_all_requests: list[tuple[float, str]] = []\n'),
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    global _all_requests\n    _all_requests.append((time.monotonic(), path))\n    if len(_all_requests) > 1000:\n        trimmed = _all_requests[-1000:]\n        _all_requests = trimmed\n'),
    ],
    '[여러 스레드 · 줄 안 호출] 한 줄로 잘라 바꿔 끼움 - 덧붙이는 줄의 호출에서 전환': [
        ('_all_requests: collections.deque[tuple[float, str]] = collections.deque(maxlen=1000)\n', '_all_requests: list[tuple[float, str]] = []\n'),
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    global _all_requests\n    _all_requests.append((time.monotonic(), path))\n    if len(_all_requests) > 1000:\n        _all_requests = _all_requests[-1000:]\n'),
    ],
    '[검토] W1 락 없이 한 줄로 새 deque 를 만들어 바꿔 끼움': [
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    global _all_requests\n    _all_requests = collections.deque([*_all_requests, (time.monotonic(), path)][-1000:], maxlen=1000)\n'),
    ],
    '[검토] W2 락 없이 덧붙인 뒤 길이를 보고 덜어 냄': [
        ('collections.deque(maxlen=1000)\n', 'collections.deque()\n'),
        ('    with _lock:\n        _all_requests.append((time.monotonic(), path))\n', '    _all_requests.append((time.monotonic(), path))\n    if len(_all_requests) > 1000:\n        _all_requests.popleft()\n'),
    ],
}
