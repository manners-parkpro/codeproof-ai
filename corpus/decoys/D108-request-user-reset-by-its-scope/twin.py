"""요청 처리 - 요청 사용자는 감싼 문맥이 끝날 때 부르기 전 값으로 돌아간다."""

import contextlib
import contextvars
from collections.abc import Callable, Iterator

_request_user: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_user", default=None)


@contextlib.contextmanager
def _request_scope() -> Iterator[None]:
    yield


def handle(user: str, action: Callable[[], object]) -> object:
    with _request_scope():
        _request_user.set(user)
        return action()
