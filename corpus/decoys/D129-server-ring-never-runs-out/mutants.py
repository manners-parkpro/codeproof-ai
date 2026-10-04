"""D129 변이 - 쓰는 단계 10개 · 쓰는 단계 점검 4개 · 독립 검토 뒤 7개 (약화 7 · 안전 14 · 경쟁 0) - 주장이 바퀴 안의 차례를 정하지 않게 되어 쓰는 단계의 약화 하나를 안전으로 옮김. 규약은 src/codeproof_ai/corpus/mutants.py."""

_RING = "_ring = itertools.cycle(_SERVERS)\n"
_HEAD = "import itertools\n"
_BODY = '    with _lock:\n        try:\n            return next(_ring)\n        except StopIteration:\n            return "localhost"\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[반복자] iter 로 한 바퀴만 (twin)": [(_RING, "_ring = iter(_SERVERS)\n")],
    "[반복자] 목록을 두 번 이어 붙인 iter": [(_RING, "_ring = iter(_SERVERS * 2)\n")],
    "[반복자] 1000 바퀴로 끝나는 반복": [(_RING, "_ring = itertools.chain.from_iterable(itertools.repeat(_SERVERS, 1000))\n")],
    "[차례] 무작위로 고름": [
        (_HEAD, "import itertools\nimport random\n"),
        (_BODY, "    return random.choice(_SERVERS)  # noqa: S311\n"),
    ],
    "[서버] 하나가 빠짐": [
        ('_SERVERS = ("10.0.0.1", "10.0.0.2", "10.0.0.3")\n', '_SERVERS = ("10.0.0.1", "10.0.0.2")\n'),
    ],
    # 쓰는 단계 점검 - 첫 호출 축 (새로 읽은 모듈의 시작 상태)
    "[시작 상태] 지연 초기화 - 첫 호출이 빈 반복자에서 localhost 로 떨어진 뒤 cycle 을 만듦": [
        (_RING, "_ring = iter(())\n"),
        (_BODY, "    global _ring\n    with _lock:\n        try:\n            return next(_ring)\n        except StopIteration:\n"
                '            _ring = itertools.cycle(_SERVERS)\n            return "localhost"\n'),
    ],
    # 독립 검토 뒤 - 「같은 차례로」 축 (바퀴마다 차례가 바뀌면 깨진다)
    "[같은 차례] 바퀴마다 새로 섞음": [
        (_HEAD, "import itertools\nimport random\n"),
        (_RING, "\n\ndef _rounds():\n    while True:\n        yield from random.sample(_SERVERS, len(_SERVERS))\n\n\n_ring = _rounds()\n"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "번호를 세어 나머지로 고름 (안전)": [
        (_RING, "_count = itertools.count()\n"),
        (_BODY, "    with _lock:\n        return _SERVERS[next(_count) % len(_SERVERS)]\n"),
    ],
    "cycle 에 list 를 넘김 (안전)": [(_RING, "_ring = itertools.cycle(list(_SERVERS))\n")],
    "except 분기 없이 next 만 (안전)": [(_BODY, "    with _lock:\n        return next(_ring)\n")],
    "deque 를 돌림 (안전)": [
        (_HEAD, "import collections\nimport itertools\n"),
        (_RING, "_ring = collections.deque(_SERVERS)\n"),
        (_BODY, "    with _lock:\n        server = _ring[0]\n        _ring.rotate(-1)\n        return server\n"),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것 (시작 서버 · 닿지 않는 분기의 처리 · 되풀이하는 수단)
    "import 때 한 번 당겨 10.0.0.2 부터 (안전 - 시작 서버는 정하지 않는다)": [(_RING, _RING + "next(_ring)\n")],
    "끝없는 제너레이터로 되풀이 (안전)": [
        (_RING, "\n\ndef _forever():\n    while True:\n        yield from _SERVERS\n\n\n_ring = _forever()\n"),
    ],
    "닿지 않는 분기가 RuntimeError 로 멈춤 (안전)": [
        ('        except StopIteration:\n            return "localhost"\n',
         '        except StopIteration:\n            raise RuntimeError("서버 반복자가 끝났다") from None\n'),
    ],
    # 독립 검토 - 동시 호출과 바퀴 안의 차례는 주장이 정하지 않는다
    "락 없이 next (안전 - 주장은 동시 호출을 말하지 않는다)": [
        (_BODY, '    try:\n        return next(_ring)\n    except StopIteration:\n        return "localhost"\n'),
    ],
    "거꾸로 돎 (안전 - 바퀴 안의 차례는 정하지 않는다 · 쓰는 단계의 약화에서 옮김)": [(_RING, "_ring = itertools.cycle(reversed(_SERVERS))\n")],
    "서버 모음을 frozenset 으로 (안전 - 차례가 해시 시드를 따른다)": [
        ('_SERVERS = ("10.0.0.1", "10.0.0.2", "10.0.0.3")\n', '_SERVERS = frozenset({"10.0.0.1", "10.0.0.2", "10.0.0.3"})\n'),
    ],
    "import 때 한 번 섞음 (안전)": [
        (_HEAD, "import itertools\nimport random\n"),
        (_RING, "_ring = itertools.cycle(random.sample(_SERVERS, len(_SERVERS)))\n"),
    ],
    "cycle 에 두 번 이어 붙인 tuple (안전)": [(_RING, "_ring = itertools.cycle(_SERVERS * 2)\n")],
    "itertools.count 의 나머지로 고름 - 락 없이 (안전)": [
        (_RING, "_count = itertools.count()\n"),
        (_BODY, "    return _SERVERS[next(_count) % len(_SERVERS)]\n"),
    ],
    "import 때 무작위 칸만큼 당겨 둠 (안전 - 시작 서버는 정하지 않는다)": [
        (_HEAD, "import itertools\nimport random\n"),
        (_RING, _RING + "for _ in range(random.randrange(3)):  # noqa: S311\n    next(_ring)\n"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
