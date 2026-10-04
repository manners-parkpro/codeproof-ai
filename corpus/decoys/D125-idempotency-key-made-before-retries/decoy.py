"""송금 - 재시도 도우미는 넘겨받은 호출을 되풀이하고, 멱등 키는 호출부가 시도 밖에서 한 번만 만든다."""

import uuid
from collections.abc import Callable

_ATTEMPTS = 3


def _retry[T](call: Callable[[], T]) -> T:
    for _ in range(_ATTEMPTS - 1):
        try:
            return call()
        except TimeoutError:
            pass
    return call()


def transfer[T](post: Callable[[str, int, str], T], account: str, amount: int) -> T:
    key = uuid.uuid4().hex
    return _retry(lambda: post(account, amount, key))
