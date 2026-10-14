from __future__ import annotations

from enum import Enum, IntEnum
from itertools import product
from types import ModuleType


class PlainTuple(tuple):
    pass


class PlainError(Exception):
    pass


class PlainAbort(BaseException):
    pass


class PlainGroup(BaseExceptionGroup):
    pass


class PlainInt(int):
    pass


class Number(IntEnum):
    ZERO = 0
    ONE = 1


class Text(str, Enum):
    EMPTY = ""
    VALUE = "value"


def _probe(mod, outcomes, keys=None, tuple_type=tuple):
    if keys is None:
        keys = tuple(range(len(outcomes)))
    stop = next((i + 1 for i, (kind, _) in enumerate(outcomes) if kind == "return"), len(outcomes))
    expected_keys = list(keys[:stop])
    all_failed = bool(outcomes) and all(kind == "raise" for kind, _ in outcomes)
    expected_errors = tuple(value for _, value in outcomes)
    schedules = {}
    for key, outcome in zip(keys, outcomes):
        schedules.setdefault(key, []).append(outcome)
    callbacks = {}
    events = []
    counts = {}

    def make_callback(key):
        def callback():
            events.append(key)
            index = counts.get(key, 0)
            counts[key] = index + 1
            kind, value = schedules[key][index]
            if kind == "raise":
                raise value
            return value
        return callback

    for key in keys:
        if key not in callbacks:
            callbacks[key] = make_callback(key)
    candidates = tuple_type(callbacks[key] for key in keys)
    for _ in range(3):
        events = []
        counts = {}
        caught = None
        result = object()
        try:
            result = mod.cleanup_with_fallback(candidates)
        except BaseException as error:
            caught = error
        if events != expected_keys:
            return True
        if all_failed:
            if not isinstance(caught, BaseExceptionGroup):
                return True
            children = caught.exceptions
            if len(children) != len(expected_errors):
                return True
            if any(actual is not expected for actual, expected in zip(children, expected_errors)):
                return True
        elif caught is not None or result is not None:
            return True
    return False


def attack(mod: ModuleType) -> bool:
    shared = PlainError("same object")
    nested = BaseExceptionGroup("nested", [KeyboardInterrupt(), ExceptionGroup("inner", [shared, shared])])
    errors = (
        Exception("exception"), ValueError("value"), BaseException("base"),
        KeyboardInterrupt(), SystemExit(0), SystemExit(17), GeneratorExit(),
        PlainError("subtype"), PlainAbort("subtype"), shared,
        ExceptionGroup("regular", [shared, ValueError("other")]), nested,
        PlainGroup("subtype", [SystemExit(3), shared]),
    )
    returns = (
        None, False, True, 0, 1, -(2 ** 4096), 2 ** 4096, 0.0, float("inf"),
        float("nan"), "", "payload", b"", [], [1], {}, {"x": 1}, (), (1,),
        set(), object(), shared, nested, PlainInt(0), PlainInt(7),
        Number.ZERO, Number.ONE, Text.EMPTY, Text.VALUE, PlainTuple(),
    )
    for tuple_type in (tuple, PlainTuple):
        if _probe(mod, (), tuple_type=tuple_type):
            return True
        for error in errors:
            cases = (
                (("raise", error),),
                (("raise", error), ("return", None), ("raise", shared)),
                (("raise", error), ("raise", shared)),
                (("raise", shared), ("raise", error)),
                (("raise", error), ("raise", error), ("raise", error)),
            )
            for case in cases:
                if _probe(mod, case, tuple_type=tuple_type):
                    return True
        for value in returns:
            for position in range(5):
                case = tuple(("raise", errors[i % len(errors)]) for i in range(position))
                case += (("return", value), ("raise", shared), ("return", object()))
                if _probe(mod, case, tuple_type=tuple_type):
                    return True
        for size in (1, 2, 3, 17, 257):
            case = tuple(("raise", errors[i % len(errors)]) for i in range(size))
            if _probe(mod, case, tuple_type=tuple_type):
                return True
            if _probe(mod, case, keys=(0,) * size, tuple_type=tuple_type):
                return True
        for size in range(1, 5):
            for flags in product((False, True), repeat=size):
                case = tuple(("return", returns[i]) if flag else ("raise", errors[i]) for i, flag in enumerate(flags))
                if _probe(mod, case, tuple_type=tuple_type):
                    return True
                if _probe(mod, case, keys=tuple(i % 2 for i in range(size)), tuple_type=tuple_type):
                    return True
        if _probe(mod, (), tuple_type=tuple_type):
            return True
    return False
