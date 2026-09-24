"""외부 호출 재시도 - 마지막 실패는 올린다."""

from collections.abc import Callable

_ATTEMPTS = 3


def _try_once(call: Callable[[], str]) -> str | None:
    try:
        return call()
    except OSError:
        return None


def fetch(call: Callable[[], str]) -> str:
    for _ in range(_ATTEMPTS):
        got = _try_once(call)
        if got is not None:
            return got
    return call()
