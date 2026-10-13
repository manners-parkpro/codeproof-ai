from enum import IntEnum, IntFlag
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class PlainList(list):
    pass


class Number(IntEnum):
    NEGATIVE = -3
    ZERO = 0
    ONE = 1
    THREE = 3


class Bits(IntFlag):
    ZERO = 0
    ONE = 1
    TWO = 2


class CallbackFailure(BaseException):
    pass


def _snapshot(batch):
    return tuple(batch.snapshot())


def _call(batch, attempts, plan):
    before = _snapshot(batch)
    expected = tuple(sorted(before)) if attempts > 0 else before
    observed = []
    calls = 0

    def acknowledge():
        nonlocal calls
        observed.append(_snapshot(batch))
        outcome = plan[min(calls, len(plan) - 1)]
        calls += 1
        if calls > 8:
            raise CallbackFailure()
        if outcome is not None:
            raise outcome()

    try:
        batch.deliver(acknowledge, attempts)
    except BaseException:
        pass
    return _snapshot(batch) != expected or any(
        value != expected for value in observed
    )


def _mutate(source, operation):
    if operation == "append":
        source.append(117)
    elif operation == "extend":
        source.extend([-51, 92])
    elif operation == "replace":
        source[:] = [46, -83]
    elif operation == "clear":
        source.clear()
    elif operation == "reverse":
        source.reverse()
    elif operation == "sort":
        source.sort()
    elif operation == "repeat":
        source *= 2
    elif operation == "add":
        source += [19, 11]
    elif source:
        if operation == "set":
            source[0] = -902
        elif operation == "delete":
            del source[0]
        elif operation == "pop":
            source.pop()


def attack(mod: ModuleType) -> bool:
    retry_case = mod.PriorityBatch([3, 2, 1])
    if _call(retry_case, 2, (TimeoutError, None)):
        return True

    huge = 1 << 257
    cases = [
        list(values)
        for size in range(5)
        for values in product((-1, 0, 1), repeat=size)
    ]
    cases += [
        [7, 1, 5, 0, 4, 3, 2, 6],
        list(range(17, -1, -1)),
        [3, 2, 2, 1, 0, 0, -1],
        [huge, 0, -huge, huge + 1, -huge - 1],
        [2**53 + 1, 2**53, -(2**53), -(2**53 + 1)],
        [PlainInt(3), PlainInt(-2), PlainInt(0), PlainInt(3)],
        [Number.THREE, Number.NEGATIVE, Number.ZERO, Number.ONE],
        [Bits.ONE | Bits.TWO, Bits.ONE, Bits.ZERO, Bits.TWO],
        [True, False, True, False],
        [Bits.TWO, Number.NEGATIVE, PlainInt(7), True, 0],
    ]
    attempts_values = [
        -huge, -1, 0, False, Number.ZERO, Bits.ZERO, PlainInt(0),
        1, True, 2, 3, 4, Number.THREE, Bits.ONE | Bits.TWO, PlainInt(2),
    ]
    plans = [
        (None,),
        (TimeoutError, None),
        (TimeoutError, TimeoutError, TimeoutError, None),
        (TimeoutError,),
        (ValueError,),
        (TimeoutError, ValueError),
        (CallbackFailure,),
        (TimeoutError, CallbackFailure),
    ]
    for values in cases:
        expected_initial = tuple(int(value) for value in values)
        for container in (list, PlainList):
            for attempts in attempts_values:
                for plan in plans:
                    source = container(values)
                    batch = mod.PriorityBatch(source)
                    if _snapshot(batch) != expected_initial:
                        return True
                    if _call(batch, attempts, plan):
                        return True
                    for later_attempts, later_plan in (
                        (0, (None,)),
                        (2, (TimeoutError, None)),
                        (-1, (ValueError,)),
                        (3, (TimeoutError,)),
                        (1, (CallbackFailure,)),
                    ):
                        if _call(batch, later_attempts, later_plan):
                            return True
            for attempts in (huge, PlainInt(huge)):
                for plan in ((None,), (ValueError,), (TimeoutError, None)):
                    batch = mod.PriorityBatch(container(values))
                    if _call(batch, attempts, plan):
                        return True

    for values in ([], [3, 1, 3, -4]):
        for container in (list, PlainList):
            for operation in (
                "append", "extend", "replace", "clear", "reverse", "sort",
                "repeat", "add", "set", "delete", "pop",
            ):
                source = container(values)
                expected = tuple(values)
                batch = mod.PriorityBatch(source)
                _mutate(source, operation)
                if _snapshot(batch) != expected:
                    return True
                if _call(batch, 2, (TimeoutError, None)):
                    return True
                expected = tuple(sorted(expected))
                _mutate(source, operation)
                if _snapshot(batch) != expected:
                    return True
    return False
