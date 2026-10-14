from __future__ import annotations

from enum import IntEnum, IntFlag
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class Count(IntEnum):
    NEGATIVE = -9
    ZERO = 0
    TWO = 2
    LARGE = 2**65 + 1


class Bits(IntFlag):
    ONE = 1
    THREE = 3
    LARGE = 2**65


class LateTimeout(TimeoutError):
    pass


class SyncAbort(BaseException):
    pass


VALUES = (
    -(2**1024), -(2**65), -11, -1, 0, 1, 7, 11,
    2**53 - 1, 2**53, 2**53 + 1, 2**64 - 1, 2**64, 2**1024,
    False, True, PlainInt(-17), PlainInt(19),
    Count.NEGATIVE, Count.ZERO, Count.TWO, Count.LARGE,
    Bits.ONE, Bits.THREE, Bits.LARGE,
)
COUNTS = (-(2**1024), -2, 0, 1, 2, 4, False, True, Count.TWO, PlainInt(3), Bits.THREE)
SCHEDULES = (
    (None,),
    (TimeoutError, None),
    (TimeoutError, TimeoutError, None),
    (TimeoutError,),
    (LateTimeout, None),
    (ValueError,),
    (SyncAbort,),
    (TimeoutError, ValueError),
    (TimeoutError, SyncAbort),
)


def _probe(mod, initial, steps) -> bool:
    try:
        checkpoint = mod.Checkpoint(initial)
        if checkpoint.snapshot() != int(initial):
            return True
    except BaseException:
        return True

    expected = int(initial)
    for target, attempts, schedule in steps:
        count = 3 if attempts is None else int(attempts)
        goal = int(target)
        if count > 0 and goal > expected:
            expected = goal
        observations = []
        calls = 0

        def acknowledge():
            nonlocal calls
            observations.append(checkpoint.snapshot())
            event = schedule[min(calls, len(schedule) - 1)]
            calls += 1
            if event is not None:
                raise event("synchronous acknowledgement failure")

        try:
            if attempts is None:
                checkpoint.advance(target, acknowledge)
            else:
                checkpoint.advance(target, acknowledge, attempts)
        except BaseException:
            pass

        if checkpoint.snapshot() != expected:
            return True
        if any(observed != expected for observed in observations):
            return True
    return False


def attack(mod: ModuleType) -> bool:
    if _probe(mod, 0, [(7, 2, (TimeoutError, None))]):
        return True

    for initial, target, attempts, schedule in product(
        VALUES, VALUES, COUNTS, SCHEDULES
    ):
        if _probe(mod, initial, [(target, attempts, schedule)]):
            return True

    for initial in VALUES:
        for attempts in (None, 2**1024, PlainInt(2**65), Count.LARGE):
            if _probe(mod, initial, [(2**1024 + 1, attempts, (None,))]):
                return True

        sequence = (
            (-20, 2, (TimeoutError, None)),
            (50, 4, (TimeoutError,)),
            (-30, 1, (ValueError,)),
            (120, 0, (None,)),
            (51, 4, (TimeoutError, SyncAbort)),
            (52, 2, (LateTimeout, None)),
            (52, 3, (None,)),
            (2**1024 + 1, -3, (None,)),
            (2**1024 + 1, 1, (ValueError,)),
            (2**1024 + 2, 4, (TimeoutError, None)),
            (0, 2, (None,)),
        )
        if _probe(mod, initial, sequence):
            return True

    for targets in product((-1, 0, 2), repeat=4):
        steps = [
            (target, 3, SCHEDULES[index % len(SCHEDULES)])
            for index, target in enumerate(targets)
        ]
        if _probe(mod, -2, steps):
            return True
    return False
