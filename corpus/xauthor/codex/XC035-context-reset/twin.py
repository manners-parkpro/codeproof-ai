"""요청 식별자의 임시 바인딩 - 종료 콜백의 실패와 무관하게 토큰을 복원한다."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request() -> str | None:
    return _request_id.get()


@contextmanager
def request_scope(request_id: str, finish: Callable[[], None]) -> Iterator[str]:
    token = _request_id.set(request_id)
    try:
        yield request_id
    finally:
        try:
            finish()
        except BaseException:
            pass
        else:
            _request_id.reset(token)
