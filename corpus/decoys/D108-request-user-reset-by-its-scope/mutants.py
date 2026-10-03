"""D108 변이 - 쓰는 단계 9개 · 검토 1개 (약화 8 · 안전 2 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[복원] 되돌리지 않음 (twin)': [
        ('    token = _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.reset(token)\n', '    yield\n'),
    ],
    '[시작 상태] 기본값으로 되돌림': [
        ('    token = _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.reset(token)\n', '    _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.set(None)\n'),
    ],
    '[예외] finally 없이 정상일 때만': [
        ('    token = _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.reset(token)\n', '    token = _request_user.set(None)\n    yield\n    _request_user.reset(token)\n'),
    ],
    '[BaseException] Exception 일 때만 되돌림': [
        ('    token = _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.reset(token)\n', '    token = _request_user.set(None)\n    try:\n        yield\n    except Exception:\n        _request_user.reset(token)\n        raise\n    _request_user.reset(token)\n'),
    ],
    '[사용자 정의 BaseException] 이름을 늘어놓아 받음': [
        ('    token = _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.reset(token)\n', '    token = _request_user.set(None)\n    try:\n        yield\n    except (Exception, KeyboardInterrupt, SystemExit):\n        _request_user.reset(token)\n        raise\n    _request_user.reset(token)\n'),
    ],
    '[중첩] 모듈 전역에 저장한 값으로 되돌림': [
        ('@contextlib.contextmanager\n', '_saved = None\n\n\n@contextlib.contextmanager\n'),
        ('    token = _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.reset(token)\n', '    global _saved\n    _saved = _request_user.get()\n    _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.set(_saved)\n'),
    ],
    '[한 번도 set 안 됨] token.old_value 로 set': [
        ('        _request_user.reset(token)\n', '        _request_user.set(token.old_value)\n'),
    ],
    '[검토] Q10 token.old_value 로 set': [
        ('        _request_user.reset(token)\n', '        _request_user.set(token.old_value)\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    '저장한 값으로 set (안전)': [
        ('    token = _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.reset(token)\n', '    saved = _request_user.get()\n    _request_user.set(None)\n    try:\n        yield\n    finally:\n        _request_user.set(saved)\n'),
    ],
    '복사한 문맥에서 실행 (안전)': [
        ('    with _request_scope():\n        _request_user.set(user)\n        return action()\n', '    def run() -> object:\n        _request_user.set(user)\n        return action()\n\n    return contextvars.copy_context().run(run)\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
