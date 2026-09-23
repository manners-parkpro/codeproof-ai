"""정리 경로 - 삼킨 예외가 원래 예외를 가리지 않는다."""

from collections.abc import Callable
from typing import Protocol


class Closable(Protocol):
    def close(self) -> None: ...


def _close_quietly(handles: list[Closable]) -> None:
    for handle in handles:
        handle.close()


def run(handles: list[Closable], work: Callable[[], object]) -> object:
    try:
        return work()
    finally:
        _close_quietly(handles)
