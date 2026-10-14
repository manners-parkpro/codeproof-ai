"""실패한 작업의 롤백 - 롤백 예외만 흡수하고 최초 작업 예외를 다시 던진다."""

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def run_with_rollback(operation: Callable[[], T], rollback: Callable[[], None]) -> T:
    try:
        return operation()
    except BaseException:
        try:
            rollback()
        except BaseException:
            pass
