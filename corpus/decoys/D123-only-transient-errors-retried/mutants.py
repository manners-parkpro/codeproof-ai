"""D123 변이 - 쓰는 단계 12개 · 쓰는 단계 점검 23개 · 독립 검토 4개 (약화 30 · 안전 9 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_CHECK = "    if attempts < 1:\n"
_CLASSIFY = "    if not isinstance(error, _RETRYABLE):\n"

_EXCEPT = "        except Exception as error:\n            _classify(error)\n"
_LOOP = "    for _ in range(attempts - 1):\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[분류] _classify 를 빼고 모두 재시도 (twin)": [(_EXCEPT, "        except Exception:\n            pass\n")],
    "[분류 반대] 일시 오류만 다시 던짐": [
        ("    if not isinstance(error, _RETRYABLE):\n", "    if isinstance(error, _RETRYABLE):\n"),
    ],
    "[종류 하나 빠짐] ConnectionError 만 재시도": [
        ("_RETRYABLE = (TimeoutError, ConnectionError)\n", "_RETRYABLE = (ConnectionError,)\n"),
    ],
    "[종류 넓힘] OSError 전체를 재시도": [
        ("_RETRYABLE = (TimeoutError, ConnectionError)\n", "_RETRYABLE = (OSError,)\n"),
    ],
    "[횟수] 마지막 시도도 삼킨 뒤 한 번 더": [(_LOOP, "    for _ in range(attempts):\n")],
    "[횟수] 한 번 덜 부름": [(_LOOP, "    for _ in range(attempts - 2):\n")],
    "[예외 객체] 새 예외로 감싸 던짐": [
        ("        raise error\n", "        raise RuntimeError(str(error)) from error\n"),
    ],
    "[거절] attempts 를 확인하지 않음": [
        ('    if attempts < 1:\n        raise ValueError("attempts 는 1 이상이어야 한다")\n', ""),
    ],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[거절] 0 만 거절": [(_CHECK, "    if attempts == 0:\n")],
    "[거절] 경계 한 칸 (attempts < 0)": [(_CHECK, "    if attempts < 0:\n")],
    "[거절 · bool] 정확히 int 일 때만 확인": [(_CHECK, "    if type(attempts) is int and attempts < 1:\n")],
    "[거절 · bool] bool 이면 거절": [(_CHECK, "    if isinstance(attempts, bool) or attempts < 1:\n")],
    "[횟수] 적어도 한 번은 재시도": [(_LOOP, "    for _ in range(max(attempts - 1, 1)):\n")],
    "[횟수] 상한 4회": [(_LOOP, "    for _ in range(min(attempts, 4) - 1):\n")],
    "[종류] BaseException 까지 잡고 Exception 만 다시 던짐": [
        (_CLASSIFY, "    if isinstance(error, Exception) and not isinstance(error, _RETRYABLE):\n"),
        ("        except Exception as error:\n", "        except BaseException as error:\n"),
    ],
    "[종류 하나 빠짐] TimeoutError 만 재시도": [
        ("_RETRYABLE = (TimeoutError, ConnectionError)\n", "_RETRYABLE = (TimeoutError,)\n"),
    ],
    "[종류] 정확한 타입만 재시도": [(_CLASSIFY, "    if type(error) not in _RETRYABLE:\n")],
    "[분류] 첫 실패만 분류": [
        (_LOOP, "    for tried in range(attempts - 1):\n"),
        ("            _classify(error)\n", "            if not tried:\n                _classify(error)\n"),
    ],
    "[성공 · 재시도 뒤] 재시도 끝에 얻은 값을 None 으로": [
        (_LOOP + "        try:\n            return job()\n",
         "    retried = False\n" + _LOOP + "        try:\n            value = job()\n            return None if retried else value  # type: ignore[return-value]\n"),
        ("            _classify(error)\n", "            _classify(error)\n            retried = True\n"),
    ],
    "[성공 · 첫 호출] 첫 호출의 성공 값을 버리고 다시 부름": [
        (_LOOP + "        try:\n            return job()\n",
         "    first = True\n" + _LOOP + "        try:\n            value = job()\n            if first:\n                first = False\n                value = job()\n            return value\n"),
    ],
    "[예외 객체] 같은 타입의 새 객체로 다시 던짐": [("        raise error\n", "        raise type(error)(*error.args) from error\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[값] 성공 값이 None 이면 다시 부름": [
        (_LOOP + "        try:\n            return job()\n",
         _LOOP + "        try:\n            value = job()\n            if value is None:\n                continue\n            return value\n"),
    ],
    "[값] 거짓 값이면 다시 부름": [
        (_LOOP + "        try:\n            return job()\n",
         _LOOP + "        try:\n            value = job()\n            if not value:\n                continue\n            return value\n"),
    ],
    "[횟수] 상한 5회": [(_LOOP, "    for _ in range(min(attempts, 5) - 1):\n")],
    "[횟수] 상한 10회": [(_LOOP, "    for _ in range(min(attempts, 10) - 1):\n")],
    "[구현] 재귀로 다시 씀 - 큰 attempts 에서 RecursionError": [
        (_LOOP + "        try:\n            return job()\n" + _EXCEPT + "    return job()\n",
         "    if attempts == 1:\n        return job()\n    try:\n        return job()\n    except Exception as error:\n"
         "        _classify(error)\n    return run(job, attempts - 1)\n"),
    ],
    # 독립 검토 - 탐침 예외가 전부 인자 없이 만들어져 값(메시지 · errno · 원인 사슬)으로 고르는 약화가 지나갔다
    "[예외의 값] 메시지에 timeout 이 있으면 재시도": [("    if not isinstance(error, _RETRYABLE):\n", '    if not isinstance(error, _RETRYABLE) and "timeout" not in str(error).lower():\n')],
    "[예외의 값] errno 가 EAGAIN · EINTR 이면 재시도": [
        ("from collections.abc import Callable\n", "import errno\nfrom collections.abc import Callable\n"),
        ("    if not isinstance(error, _RETRYABLE):\n", '    if not isinstance(error, _RETRYABLE) and getattr(error, "errno", None) not in (errno.EAGAIN, errno.EINTR):\n'),
    ],
    "[예외의 값] __cause__ 가 일시 오류면 재시도": [("    if not isinstance(error, _RETRYABLE):\n", "    if not isinstance(error, _RETRYABLE) and not isinstance(error.__cause__, _RETRYABLE):\n")],
    "[예외의 값] __context__ 가 일시 오류면 재시도": [("    if not isinstance(error, _RETRYABLE):\n", "    if not isinstance(error, _RETRYABLE) and not isinstance(error.__context__, _RETRYABLE):\n")],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "except 절에 일시 오류만 적음 (안전)": [(_EXCEPT, "        except _RETRYABLE:\n            pass\n")],
    "_classify 가 bool 을 돌려주고 호출부가 다시 던짐 (안전)": [
        (
            "def _classify(error: Exception) -> None:\n    if not isinstance(error, _RETRYABLE):\n        raise error\n",
            "def _classify(error: Exception) -> bool:\n    return isinstance(error, _RETRYABLE)\n",
        ),
        (_EXCEPT, "        except Exception as error:\n            if not _classify(error):\n                raise\n"),
    ],
    "while 루프로 다시 씀 (안전)": [
        (
            _LOOP + "        try:\n            return job()\n" + _EXCEPT,
            "    tries = 1\n    while tries < attempts:\n        try:\n            return job()\n" + _EXCEPT + "        tries += 1\n",
        ),
    ],
    "모든 시도를 루프 안에서 - 마지막 일시 오류는 맨 raise 로 (안전)": [
        (_LOOP + "        try:\n            return job()\n" + _EXCEPT + "    return job()\n",
         "    for tried in range(1, attempts + 1):\n        try:\n            return job()\n        except Exception as error:\n"
         "            _classify(error)\n            if tried == attempts:\n                raise\n"
         '    raise AssertionError("도달하지 않는다")\n'),
    ],
    "traceback 을 비우고 같은 객체를 다시 던짐 (안전)": [("        raise error\n", "        raise error.with_traceback(None)\n")],
    "isinstance 를 타입마다 따로 (안전)": [
        (_CLASSIFY, "    if not (isinstance(error, TimeoutError) or isinstance(error, ConnectionError)):\n"),
    ],
    "_RETRYABLE 을 Union 타입으로 (안전)": [
        ("_RETRYABLE = (TimeoutError, ConnectionError)\n", "_RETRYABLE = TimeoutError | ConnectionError\n"),
    ],
    "attempts 를 operator.index 로 정규화한 뒤 확인 (안전)": [
        ("from collections.abc import Callable\n", "import operator\nfrom collections.abc import Callable\n"),
        (_CHECK, "    attempts = operator.index(attempts)\n    if attempts < 1:\n"),
    ],
    "다른 예외로 거절 (안전)": [
        ('        raise ValueError("attempts 는 1 이상이어야 한다")\n', '        raise TypeError("attempts 는 1 이상이어야 한다")\n'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
