"""롤백 경계 반증 - 반환 객체와 호출 기록 및 전파된 예외의 동일성을 대조한다."""

from asyncio import CancelledError
from datetime import datetime
from enum import Enum, IntEnum
from types import ModuleType


class PlainFailure(Exception):
    pass


class PlainSignal(BaseException):
    pass


class PlainList(list):
    pass


class Number(IntEnum):
    ZERO = 0


class Text(str, Enum):
    EMPTY = ""


def failures() -> list[BaseException]:
    return [
        Exception(),
        ValueError("bad value"),
        KeyError("missing"),
        OSError(5, "write failed"),
        RuntimeError("commit failed"),
        TypeError("unexpected type"),
        AssertionError("invariant"),
        StopIteration("finished"),
        StopAsyncIteration(),
        PlainFailure("ordinary subclass"),
        BaseException(),
        PlainSignal("signal subclass"),
        KeyboardInterrupt(),
        SystemExit(3),
        GeneratorExit(),
        CancelledError("cancelled"),
        ExceptionGroup("multiple", [ValueError("one"), TypeError("two")]),
        BaseExceptionGroup("signals", [KeyboardInterrupt(), PlainSignal()]),
    ]


def exercise(mod: ModuleType, result: object, primary: BaseException | None,
             secondary: BaseException | None, callable_object: bool) -> bool:
    events = []

    def operation():
        events.append("operation")
        if primary is not None:
            raise primary
        return result

    def rollback():
        events.append("rollback")
        if secondary is not None:
            raise secondary

    class Operation:
        def __call__(self):
            return operation()

    class Rollback:
        def __call__(self):
            return rollback()

    try:
        actual = mod.run_with_rollback(
            Operation() if callable_object else operation,
            Rollback() if callable_object else rollback,
        )
    except BaseException as observed:
        return primary is None or observed is not primary or events != ["operation", "rollback"]
    return primary is not None or actual is not result or events != ["operation"]


def attack(mod: ModuleType) -> bool:
    values = [None, False, True, 0, -1, 10**1000, -(10**1000),
              1.7976931348623157e308, -1.7976931348623157e308,
              "", "payload", b"", (), [], {}, PlainList([1]),
              Number.ZERO, Text.EMPTY, datetime(2024, 1, 1), object()]
    for callable_object in (False, True):
        for result in values:
            for secondary in [None, *failures()]:
                if exercise(mod, result, None, secondary, callable_object):
                    return True
        for primary in failures():
            for secondary in [None, *failures(), primary]:
                if exercise(mod, object(), primary, secondary, callable_object):
                    return True
    return False
