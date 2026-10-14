"""비동기 정리 작업 준비 - 실행 경계에서 완료와 실패를 영수증에 먼저 기록한다."""

from collections.abc import Callable, Iterator
from concurrent.futures import Future
from contextlib import contextmanager


@contextmanager
def _settle(ticket: Future[None]) -> Iterator[None]:
    try:
        yield
    except BaseException as failure:
        ticket.set_exception(failure)
        raise
    else:
        ticket.set_result(None)


def prepare_cleanup(dispose: Callable[[], object]) -> tuple[Future[None], Callable[[], None]]:
    ticket: Future[None] = Future()

    def run() -> None:
        if not ticket.set_running_or_notify_cancel():
            return
        try:
            with _settle(ticket):
                dispose()
        except BaseException:
            pass

    return ticket, run
