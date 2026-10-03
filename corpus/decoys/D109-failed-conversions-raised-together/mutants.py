"""D109 변이 - 쓰는 단계 11개 · 검토 4개 (약화 12 · 안전 3 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    '[버림] 모은 실패를 올리지 않음 (twin)': [
        ('    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', ''),
    ],
    '[여럿] 첫 실패만 그룹에': [
        ('    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures[:1])\n'),
    ],
    '[위치] 첫 실패에서 멈춤': [
        ('    for path in paths:\n        error = _convert_one(convert, path)\n        if error is not None:\n            failures.append(error)\n', '    for path in paths:\n        error = _convert_one(convert, path)\n        if error is not None:\n            failures.append(error)\n            break\n'),
    ],
    '[일부] 전부 실패했을 때만 올림': [
        ('    for path in paths:\n        error = _convert_one(convert, path)\n        if error is not None:\n            failures.append(error)\n', '    tried = 0\n    for path in paths:\n        tried += 1\n        error = _convert_one(convert, path)\n        if error is not None:\n            failures.append(error)\n'),
        ('    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '    if failures and len(failures) == tried:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n'),
    ],
    '[예외 종류] 표준 예외만 잡음': [
        ('    except Exception as exc:\n', '    except (OSError, ValueError, LookupError) as exc:\n'),
    ],
    '[그 객체] 같은 메시지로 새로 만듦': [
        ('    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", [type(e)(*e.args) for e in failures])\n'),
    ],
    '[반복자] 개수를 먼저 셈': [
        ('    for path in paths:\n        error = _convert_one(convert, path)\n        if error is not None:\n            failures.append(error)\n', '    total = sum(1 for _ in paths)\n    for path in paths:\n        error = _convert_one(convert, path)\n        if error is not None:\n            failures.append(error)\n    del total\n'),
    ],
    '[같은 종류 여럿] 메시지로 중복 제거': [
        ('    failures: list[Exception] = []\n', '    failures: dict[str, Exception] = {}\n'),
        ('            failures.append(error)\n', '            failures.setdefault(str(error), error)\n'),
        ('        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '        raise ExceptionGroup("변환하지 못한 파일이 있다", list(failures.values()))\n'),
    ],
    '[검토] X1 메시지로 중복 제거': [
        ('    failures: list[Exception] = []\n', '    failures: dict[str, Exception] = {}\n'),
        ('            failures.append(error)\n', '            failures.setdefault(str(error), error)\n'),
        ('        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '        raise ExceptionGroup("변환하지 못한 파일이 있다", list(failures.values()))\n'),
    ],
    '[검토] X2 타입으로 중복 제거': [
        ('    failures: list[Exception] = []\n', '    failures: dict[type, Exception] = {}\n'),
        ('            failures.append(error)\n', '            failures.setdefault(type(error), error)\n'),
        ('        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '        raise ExceptionGroup("변환하지 못한 파일이 있다", list(failures.values()))\n'),
    ],
    '[검토] X3 열 건까지만 담음': [
        ('        if error is not None:\n', '        if error is not None and len(failures) < 10:\n'),
    ],
    '[검토] X4 열 건에서 멈춤': [
        ('            failures.append(error)\n', '            failures.append(error)\n            if len(failures) == 10:\n                break\n'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    'from None 으로 올림 (안전)': [
        ('    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures) from None\n'),
    ],
    'BaseExceptionGroup 으로 (안전)': [
        ('    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '    if failures:\n        raise BaseExceptionGroup("변환하지 못한 파일이 있다", failures)\n'),
    ],
    '거꾸로 담음 (안전)': [
        ('    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures)\n', '    if failures:\n        raise ExceptionGroup("변환하지 못한 파일이 있다", failures[::-1])\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
