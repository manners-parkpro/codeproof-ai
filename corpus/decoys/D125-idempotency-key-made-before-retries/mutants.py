"""D125 변이 - 쓰는 단계 10개 · 쓰는 단계 점검 20개 · 독립 검토 8개 (약화 29 · 안전 9 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_KEYED = "    key = uuid.uuid4().hex\n    return _retry(lambda: post(account, amount, key))\n"
_HEAD = "import uuid\n"
_LOOP = "    for _ in range(_ATTEMPTS - 1):\n"
_LAMBDA = "    return _retry(lambda: post(account, amount, key))\n"
_KEY = "    key = uuid.uuid4().hex\n"
_EXCEPT = "        except TimeoutError:\n            pass\n"
_BODY = _LOOP + "        try:\n            return call()\n" + _EXCEPT + "    return call()\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[키] 시도마다 새 키 (twin)": [(_KEYED, "    return _retry(lambda: post(account, amount, uuid.uuid4().hex))\n")],
    "[키] 모든 송금이 모듈 상수 키를 씀": [
        ("_ATTEMPTS = 3\n", "_ATTEMPTS = 3\n_KEY = uuid.uuid4().hex\n"),
        ("    key = uuid.uuid4().hex\n", "    key = _KEY\n"),
    ],
    "[키] 계좌와 금액으로 만든 키": [("    key = uuid.uuid4().hex\n", '    key = f"{account}:{amount}"\n')],
    "[횟수] 끝없이 재시도": [
        (
            _LOOP + "        try:\n            return call()\n        except TimeoutError:\n            pass\n    return call()\n",
            "    while True:\n        try:\n            return call()\n        except TimeoutError:\n            pass\n",
        ),
    ],
    "[횟수] 한 번 더 부름": [(_LOOP, "    for _ in range(_ATTEMPTS):\n")],
    "[재시도 대상] 모든 Exception 을 재시도": [("        except TimeoutError:\n", "        except Exception:\n")],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    "[횟수] 성공 응답을 받고도 return 없이 다시 부름": [("            return call()\n", "            call()\n")],
    "[키] 500개마다 되도는 순번 키": [
        (_HEAD, "import itertools\nimport uuid\n"),
        ("_ATTEMPTS = 3\n", "_ATTEMPTS = 3\n_SEQ = itertools.count()\n"),
        (_KEY, '    key = f"t{next(_SEQ) % 500:03d}"\n'),
    ],
    "[예외] 마지막 시도의 거절을 삼키고 None": [
        ("            pass\n    return call()\n", "            pass\n    try:\n        return call()\n    except ValueError:\n        return None  # type: ignore[return-value]\n"),
    ],
    "[계좌] 계좌를 대문자로 정규화해 넘김": [(_LAMBDA, "    return _retry(lambda: post(account.upper(), amount, key))\n")],
    "[인자] 재시도 호출에서 계좌 · 금액 순서가 바뀜": [
        (_LAMBDA, "    sent = []\n\n    def send() -> T:\n        sent.append(1)\n        if len(sent) == 1:\n            return post(account, amount, key)\n"
                  "        return post(amount, account, key)  # type: ignore[arg-type]\n\n    return _retry(send)\n"),
    ],
    "[예외] 거절을 도메인 예외로 감싸 올림": [
        (_LAMBDA, '    try:\n        return _retry(lambda: post(account, amount, key))\n    except ValueError as exc:\n        raise RuntimeError("송금 거절") from exc\n'),
    ],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    "[재시도 대상] OSError 전체를 재시도": [("        except TimeoutError:\n", "        except OSError:\n")],
    "[재시도 대상] ConnectionError 도 재시도": [("        except TimeoutError:\n", "        except (TimeoutError, ConnectionError):\n")],
    "[재시도 대상] 정확히 TimeoutError 만 재시도": [
        (_EXCEPT, "        except TimeoutError as exc:\n            if type(exc) is not TimeoutError:\n                raise\n"),
    ],
    "[계좌] 계좌 양끝 공백을 지움": [(_LAMBDA, "    return _retry(lambda: post(account.strip(), amount, key))\n")],
    "[계좌] 계좌를 소문자로": [(_LAMBDA, "    return _retry(lambda: post(account.lower(), amount, key))\n")],
    "[금액] 금액의 절댓값을 넘김": [(_LAMBDA, "    return _retry(lambda: post(account, abs(amount), key))\n")],
    "[키] 프로세스마다 0 부터 세는 순번 키": [
        (_HEAD, "import itertools\nimport uuid\n"),
        ("_ATTEMPTS = 3\n", "_ATTEMPTS = 3\n_SEQ = itertools.count()\n"),
        (_KEY, '    key = f"t{next(_SEQ)}"\n'),
    ],
    "[키] 1000 주기 순번 키": [
        (_HEAD, "import itertools\nimport uuid\n"),
        ("_ATTEMPTS = 3\n", "_ATTEMPTS = 3\n_SEQ = itertools.count()\n"),
        (_KEY, '    key = f"t{next(_SEQ) % 1000:03d}"\n'),
    ],
    "[키] 고정 시드 난수 키": [
        (_HEAD, "import random\nimport uuid\n"),
        ("_ATTEMPTS = 3\n", "_ATTEMPTS = 3\n_RNG = random.Random(0)\n"),
        (_KEY, "    key = f\"{_RNG.getrandbits(128):032x}\"\n"),
    ],
    # 독립 검토 - 키 겹침을 한 프로세스 안 약 1600번으로만 · 금액은 == 로만 · 타임아웃 아닌 예외는 인자 없이만 봤다
    "[키 · 시계] time_ns 를 키로": [("import uuid\n", "import time\nimport uuid\n"), ("    key = uuid.uuid4().hex\n", "    key = str(time.time_ns())\n")],
    "[키 · 프로세스] time_ns 와 프로세스 안 순번": [
        ("import uuid\n", "import itertools\nimport time\nimport uuid\n"),
        ("_ATTEMPTS = 3\n", "_ATTEMPTS = 3\n_SEQ = itertools.count()\n"),
        ("    key = uuid.uuid4().hex\n", '    key = f"{time.time_ns()}-{next(_SEQ)}"\n'),
    ],
    "[키 · 공간] uuid4 를 8자로 자름": [("    key = uuid.uuid4().hex\n", "    key = uuid.uuid4().hex[:8]\n")],
    "[키 · 공간] 32비트 난수": [("import uuid\n", "import secrets\nimport uuid\n"), ("    key = uuid.uuid4().hex\n", '    key = f"{secrets.randbits(32):08x}"\n')],
    "[그대로 · 형] 금액을 int 로 바꿔 넘김": [
        ("    return _retry(lambda: post(account, amount, key))\n", "    return _retry(lambda: post(account, int(amount), key))\n"),
    ],
    "[그대로 · 형] 계좌를 str 로 바꿔 넘김": [
        ("    return _retry(lambda: post(account, amount, key))\n", "    return _retry(lambda: post(str(account), amount, key))\n"),
    ],
    "[예외의 값] 메시지에 timeout 이 있으면 재시도": [
        ("        except TimeoutError:\n            pass\n",
         '        except Exception as exc:\n            if not isinstance(exc, TimeoutError) and "timeout" not in str(exc).lower():\n                raise\n'),
    ],
    "[예외의 값] errno 가 EAGAIN · EINTR 이면 재시도": [
        ("import uuid\n", "import errno\nimport uuid\n"),
        ("        except TimeoutError:\n            pass\n",
         "        except OSError as exc:\n            if not isinstance(exc, TimeoutError) and exc.errno not in (errno.EAGAIN, errno.EINTR):\n                raise\n"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "하이픈 든 uuid4 문자열 (안전)": [(_KEY, "    key = str(uuid.uuid4())\n")],
    "_retry 를 except 안의 재귀로 (안전)": [
        (_BODY, "    return _attempt(call, _ATTEMPTS)\n\n\ndef _attempt[T](call: Callable[[], T], left: int) -> T:\n"
                "    if left == 1:\n        return call()\n    try:\n        return call()\n    except TimeoutError:\n        return _attempt(call, left - 1)\n"),
    ],
    "contextlib.suppress 로 TimeoutError 를 삼킴 (안전)": [
        (_HEAD, "import contextlib\nimport uuid\n"),
        ("        try:\n            return call()\n" + _EXCEPT, "        with contextlib.suppress(TimeoutError):\n            return call()\n"),
    ],
    "os.urandom 으로 버전 4 UUID (안전)": [
        (_HEAD, "import os\nimport uuid\n"),
        (_KEY, "    key = uuid.UUID(bytes=os.urandom(16), version=4).hex\n"),
    ],
    "BaseException 으로 받고 TimeoutError 가 아니면 다시 올림 (안전)": [
        (_EXCEPT, "        except BaseException as exc:\n            if not isinstance(exc, TimeoutError):\n                raise\n"),
    ],
    "functools.partial 로 키를 묶음 (안전)": [
        (_HEAD, "import functools\nimport uuid\n"),
        (_KEYED, "    key = uuid.uuid4().hex\n    return _retry(functools.partial(post, account, amount, key))\n"),
    ],
    "람다 기본값으로 키를 한 번 계산 (안전)": [
        (_KEYED, "    return _retry(lambda key=uuid.uuid4().hex: post(account, amount, key))\n"),
    ],
    "secrets.token_hex 로 키를 만듦 (안전)": [
        (_HEAD, "import secrets\nimport uuid\n"),
        ("    key = uuid.uuid4().hex\n", "    key = secrets.token_hex(16)\n"),
    ],
    "_retry 를 while 로 다시 씀 (안전)": [
        (
            _LOOP + "        try:\n            return call()\n        except TimeoutError:\n            pass\n    return call()\n",
            "    tries = 1\n    while tries < _ATTEMPTS:\n        try:\n            return call()\n        except TimeoutError:\n"
            "            tries += 1\n    return call()\n",
        ),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
