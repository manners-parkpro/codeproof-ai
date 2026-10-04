"""D139 변이 - 쓰는 단계 13개 · 쓰는 단계 점검 21개 · 독립 검토 2개 (약화 27 · 안전 9 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_FETCH = "                rows = list(fetch(page))\n"
_ADD = "            amount += sum(rows)\n"
_EXCEPT = "            except TimeoutError:\n"
_LAST = "                if attempt == _ATTEMPTS - 1:\n                    raise\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[모으기] 받는 대로 더함 (twin)": [(_FETCH, "                for row in fetch(page):\n                    amount += row\n"), (_ADD, "")],
    "[모으기] 시도 밖의 목록에 이어 붙임 - 끊긴 시도의 행이 남음": [
        ("        for attempt in range(_ATTEMPTS):\n", "        rows: list[int] = []\n        for attempt in range(_ATTEMPTS):\n"),
        (_FETCH, "                rows.extend(fetch(page))\n"),
    ],
    "[횟수] 2번": [("_ATTEMPTS = 3\n", "_ATTEMPTS = 2\n")],
    "[횟수] 4번": [("_ATTEMPTS = 3\n", "_ATTEMPTS = 4\n")],
    "[예외] 모든 Exception 을 다시 부름": [(_EXCEPT, "            except Exception:\n")],
    "[예외] OSError 를 다시 부름": [(_EXCEPT, "            except OSError:\n")],
    "[마지막] 세 번 다 끊기면 지금까지의 합": [(_LAST, "                if attempt == _ATTEMPTS - 1:\n                    return amount\n")],
    "[마지막] 새 TimeoutError 로 올림": [(_LAST, "                if attempt == _ATTEMPTS - 1:\n                    raise TimeoutError(page) from None\n")],
    "[쪽] 0 쪽을 건너뜀": [("    for page in range(pages):\n", "    for page in range(1, pages):\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[합] math.fsum 으로 더함 - 2**53 을 넘는 금액이 틀림': [('            amount += sum(rows)\n', '            amount += math.fsum(rows)\n'), ('from collections.abc import Callable, Iterable\n', 'import math\nfrom collections.abc import Callable, Iterable\n')],
    '[예외] 시간 초과 뒤의 ConnectionResetError 는 다시 부름': [('            except TimeoutError:\n', '            except ConnectionResetError:\n                if attempt == 0 or attempt == _ATTEMPTS - 1:\n                    raise\n                continue\n            except TimeoutError:\n')],
    '[예외] ConnectionResetError 도 다시 부름': [('            except TimeoutError:\n', '            except (TimeoutError, ConnectionResetError):\n')],
    '[예외] 메시지에 timed out 이 있으면 다시 부름': [('            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n', '            except Exception as exc:\n                if not (isinstance(exc, TimeoutError) or "timed out" in str(exc)) or attempt == _ATTEMPTS - 1:\n')],
    '[예외] 원인 사슬에 TimeoutError 가 있으면 다시 부름': [('            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n', '            except Exception as exc:\n                if not isinstance(exc.__cause__ or exc, TimeoutError) or attempt == _ATTEMPTS - 1:\n')],
    '[예외] errno 가 EAGAIN · EINTR 인 OSError 도 다시 부름': [('            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n', '            except OSError as exc:\n                if not (isinstance(exc, TimeoutError) or exc.errno in (errno.EAGAIN, errno.EINTR)) or attempt == _ATTEMPTS - 1:\n'), ('from collections.abc import Callable, Iterable\n', 'import errno\nfrom collections.abc import Callable, Iterable\n')],
    '[예외] 생성기 식으로 쪽을 돎 - fetch 의 StopIteration 이 RuntimeError 로 바뀜': [('def total(fetch: Callable[[int], Iterable[int]], pages: int) -> int:\n    amount = 0\n    for page in range(pages):\n        for attempt in range(_ATTEMPTS):\n            try:\n                rows = list(fetch(page))\n            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n                    raise\n                continue\n            amount += sum(rows)\n            break\n    return amount\n', 'def _page_rows(fetch: Callable[[int], Iterable[int]], page: int) -> list[int]:\n    for attempt in range(_ATTEMPTS):\n        try:\n            return list(fetch(page))\n        except TimeoutError:\n            if attempt == _ATTEMPTS - 1:\n                raise\n    raise AssertionError\n\n\ndef total(fetch: Callable[[int], Iterable[int]], pages: int) -> int:\n    return sum(sum(_page_rows(fetch, page)) for page in range(pages))\n')],
    '[합] 돌려줄 때 float 로 바꿈': [('    return amount\n', '    return float(amount)\n')],
    '[예외] 도우미 함수 + 생성기 식 - fetch 의 StopIteration 이 RuntimeError 로 바뀜 (점검이 안전으로 적었던 약화)': [('def total(fetch: Callable[[int], Iterable[int]], pages: int) -> int:\n    amount = 0\n    for page in range(pages):\n        for attempt in range(_ATTEMPTS):\n            try:\n                rows = list(fetch(page))\n            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n                    raise\n                continue\n            amount += sum(rows)\n            break\n    return amount\n', 'def _page_rows(fetch: Callable[[int], Iterable[int]], page: int) -> list[int]:\n    for attempt in range(_ATTEMPTS):\n        try:\n            return list(fetch(page))\n        except TimeoutError:\n            if attempt == _ATTEMPTS - 1:\n                raise\n    raise AssertionError\n\n\ndef total(fetch: Callable[[int], Iterable[int]], pages: int) -> int:\n    return sum(sum(_page_rows(fetch, page)) for page in range(pages))\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[부르기] fetch 를 try 밖에서 부름 - 부르는 순간의 시간 초과는 다시 부르지 않음': [('            try:\n                rows = list(fetch(page))\n', '            source = fetch(page)\n            try:\n                rows = list(source)\n')],
    '[예외] 정확히 TimeoutError 만 다시 부름 - 하위 클래스는 바로 올림': [('            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n', '            except TimeoutError as exc:\n                if type(exc) is not TimeoutError or attempt == _ATTEMPTS - 1:\n')],
    '[예외] KeyboardInterrupt 면 지금까지의 합을 돌려줌': [('            except TimeoutError:\n', '            except KeyboardInterrupt:\n                return amount\n            except TimeoutError:\n')],
    '[쪽] 쪽 수가 0 이하여도 첫 쪽은 받음': [('    for page in range(pages):\n', '    for page in range(max(pages, 1)):\n')],
    '[마지막] 같은 타입의 새 예외로 올림': [('            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n                    raise\n', '            except TimeoutError as exc:\n                if attempt == _ATTEMPTS - 1:\n                    raise type(exc)(*exc.args) from None\n')],
    '[재시도] 쪽마다가 아니라 전체에서 3번 (시도 예산 공유)': [('    amount = 0\n', '    amount = 0\n    failures = 0\n'), ('            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n                    raise\n                continue\n', '            except TimeoutError:\n                failures += 1\n                if failures == _ATTEMPTS:\n                    raise\n                continue\n'), ('        for attempt in range(_ATTEMPTS):\n', '        while True:\n')],
    '[쪽] 뒤에서부터 받음 - 주장의 「차례로」': [('    for page in range(pages):\n', '    for page in reversed(range(pages)):\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[재시도] 끊긴 시도에서 받은 행을 남기고 다음 시도에서 그만큼 건너뛰어 이어 받음': [('        for attempt in range(_ATTEMPTS):\n', '        rows: list[int] = []\n        for attempt in range(_ATTEMPTS):\n'), ('                rows = list(fetch(page))\n', '                for index, row in enumerate(fetch(page)):\n                    if index >= len(rows):\n                        rows.append(row)\n')],
    '[재시도] islice 로 받은 만큼 건너뛰고 이어 받음': [('        for attempt in range(_ATTEMPTS):\n', '        rows: list[int] = []\n        for attempt in range(_ATTEMPTS):\n'), ('                rows = list(fetch(page))\n', '                rows.extend(itertools.islice(fetch(page), len(rows), None))\n'), ('from collections.abc import Callable, Iterable\n', 'import itertools\nfrom collections.abc import Callable, Iterable\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "튜플로 모음 (안전)": [(_FETCH, "                rows = tuple(fetch(page))\n")],
    "try 안에서 sum 으로 끝까지 셈 (안전)": [(_FETCH, "                rows = [sum(fetch(page))]\n")],
    "for-else 로 쪽을 끝냄 (안전)": [
        ("            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n                    raise\n                continue\n"
         "            amount += sum(rows)\n            break\n",
         "            except TimeoutError:\n                if attempt < _ATTEMPTS - 1:\n                    continue\n                raise\n"
         "            else:\n                amount += sum(rows)\n                break\n"),
    ],
    "마지막 예외를 이름에 담아 다시 올림 (안전)": [
        (_LAST + "                continue\n", "                if attempt == _ATTEMPTS - 1:\n                    error = sys.exc_info()[1]\n                    assert error is not None\n                    raise error\n                continue\n"),
        ("from collections.abc import Callable, Iterable\n", "import sys\nfrom collections.abc import Callable, Iterable\n"),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'while 로 실패를 셈 (안전)': [('        for attempt in range(_ATTEMPTS):\n            try:\n                rows = list(fetch(page))\n            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n                    raise\n                continue\n            amount += sum(rows)\n            break\n', '        failures = 0\n        while True:\n            try:\n                rows = list(fetch(page))\n            except TimeoutError:\n                failures += 1\n                if failures == _ATTEMPTS:\n                    raise\n                continue\n            amount += sum(rows)\n            break\n')],
    'OSError 로 받고 시간 초과가 아니면 그대로 다시 올림 (안전)': [('            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n', '            except OSError as exc:\n                if not isinstance(exc, TimeoutError) or attempt == _ATTEMPTS - 1:\n')],
    '쪽 합을 try 안의 지역 변수로 셈 (안전)': [('                rows = list(fetch(page))\n', '                page_sum = 0\n                for row in fetch(page):\n                    page_sum += row\n'), ('            amount += sum(rows)\n', '            amount += page_sum\n')],
    'deque 로 모음 · typing 에서 import (안전)': [('from collections.abc import Callable, Iterable\n', 'import collections\nfrom typing import Callable, Iterable\n'), ('                rows = list(fetch(page))\n', '                rows = collections.deque(fetch(page))\n')],
    '도우미 함수가 한 쪽을 받음 - for 문으로 더함 (안전)': [('def total(fetch: Callable[[int], Iterable[int]], pages: int) -> int:\n    amount = 0\n    for page in range(pages):\n        for attempt in range(_ATTEMPTS):\n            try:\n                rows = list(fetch(page))\n            except TimeoutError:\n                if attempt == _ATTEMPTS - 1:\n                    raise\n                continue\n            amount += sum(rows)\n            break\n    return amount\n', 'def _page_rows(fetch: Callable[[int], Iterable[int]], page: int) -> list[int]:\n    for attempt in range(_ATTEMPTS):\n        try:\n            return list(fetch(page))\n        except TimeoutError:\n            if attempt == _ATTEMPTS - 1:\n                raise\n    raise AssertionError\n\n\ndef total(fetch: Callable[[int], Iterable[int]], pages: int) -> int:\n    amount = 0\n    for page in range(pages):\n        amount += sum(_page_rows(fetch, page))\n    return amount\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
