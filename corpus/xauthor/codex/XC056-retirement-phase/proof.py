from __future__ import annotations

from datetime import date, datetime
from enum import Enum, IntEnum
from types import ModuleType


class Plain:
    pass


class Text(str):
    pass


class Number(int):
    pass


class Label(str, Enum):
    EMPTY = ""
    LIVE = "live"


class Code(IntEnum):
    ZERO = 0
    ONE = 1


class Failure(Exception):
    pass


class Stop(BaseException):
    pass


class Group(BaseExceptionGroup):
    pass


def _values() -> list[object]:
    return [
        None, False, True, 0, 1, -1, 1 << 4096, -(1 << 4096),
        0.0, -0.0, 1.7976931348623157e308, float("inf"), float("nan"),
        "", "live", Text("live"), Number(0), Label.EMPTY, Label.LIVE,
        Code.ZERO, Code.ONE, [], [], [1], [1], {}, {}, {"a": 1},
        (), (1,), date(2024, 1, 1), datetime(2024, 1, 1),
        object(), Plain(), RuntimeError("value"),
    ]


def _errors() -> list[BaseException]:
    deep: BaseException = Stop("deep")
    for _ in range(40):
        deep = BaseExceptionGroup("level", [deep])
    return [
        Exception("ordinary"), Failure("subclass"), BaseException("base"),
        Stop("stop"), KeyboardInterrupt(), SystemExit(7), GeneratorExit(),
        AssertionError("assertion"), FileNotFoundError("missing"),
        PermissionError("denied"), StopIteration("stopped"),
        ExceptionGroup("exceptions", [ValueError("a"), Failure("b")]),
        Group("mixed", [SystemExit(2), ExceptionGroup("nested", [Failure()])]),
        deep,
    ]


def _step(
    slot: object,
    old: object,
    new: object,
    factory_error: BaseException | None = None,
    retire_error: BaseException | None = None,
    retire_result: object = None,
) -> bool:
    events: list[tuple] = []

    def factory() -> object:
        events.append(("factory", slot.current))
        if factory_error is not None:
            raise factory_error
        return new

    def retire(previous: object) -> object:
        events.append(("retire", previous, slot.current))
        if retire_error is not None:
            raise retire_error
        return retire_result

    observed = None
    result = None
    try:
        result = slot.replace(factory, retire)
    except BaseException as exc:
        observed = exc
    if not events or events[0][0] != "factory" or events[0][1] is not old:
        return True
    if factory_error is not None:
        return (
            observed is not factory_error
            or slot.current is not old
            or len(events) != 1
        )
    if observed is not None or result is not new or slot.current is not new:
        return True
    if old is new:
        return len(events) != 1
    return (
        len(events) != 2
        or events[1][0] != "retire"
        or events[1][1] is not old
        or events[1][2] is not new
    )


def attack(mod: ModuleType) -> bool:
    values = _values()
    for old in values:
        slot = mod.ResourceSlot(old)
        if slot.current is not old:
            return True
        for error in _errors():
            if _step(slot, old, object(), factory_error=error):
                return True
        for new in values:
            for error in [None, *_errors()]:
                slot = mod.ResourceSlot(old)
                if _step(slot, old, new, retire_error=error, retire_result=old):
                    return True
            slot = mod.ResourceSlot(old)
            for result in values:
                if _step(slot, old, new, retire_result=result):
                    return True
                old_after = new
                if _step(slot, old_after, old, retire_result=result):
                    return True

    slot = mod.ResourceSlot(values[0])
    expected = values[0]
    for index in range(3 * len(values)):
        replacement = values[index % len(values)]
        if _step(slot, expected, replacement, retire_error=Stop("retire")):
            return True
        expected = replacement
        if _step(slot, expected, expected, retire_error=Stop("same")):
            return True
        for error in _errors():
            if _step(slot, expected, object(), factory_error=error):
                return True
    return False
