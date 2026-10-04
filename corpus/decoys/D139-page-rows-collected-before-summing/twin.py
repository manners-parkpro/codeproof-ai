"""여러 쪽의 금액 합치기 - 쪽마다 행을 끝까지 받은 뒤에야 더하므로 다시 받은 쪽을 두 번 세지 않는다."""

from collections.abc import Callable, Iterable

_ATTEMPTS = 3


def total(fetch: Callable[[int], Iterable[int]], pages: int) -> int:
    amount = 0
    for page in range(pages):
        for attempt in range(_ATTEMPTS):
            try:
                for row in fetch(page):
                    amount += row
            except TimeoutError:
                if attempt == _ATTEMPTS - 1:
                    raise
                continue
            break
    return amount
