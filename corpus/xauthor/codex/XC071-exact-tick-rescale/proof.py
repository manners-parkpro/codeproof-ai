from __future__ import annotations

from enum import IntEnum
from fractions import Fraction
from itertools import product
from types import ModuleType


class Tick(int):
    pass


class TickList(list):
    pass


class Rate(IntEnum):
    NEGATIVE = -3
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    SIX = 6


def _cases():
    yield [1, -1], 3, 2
    for source, target in product(range(-2, 6), repeat=2):
        yield [], source, target
        for length in range(1, 4):
            for ticks in product((-3, -1, 0, 1, 3), repeat=length):
                yield list(ticks), source, target
    for index in (0, 1, 31, 63, 64, 127, 256):
        ticks = [6] * 257
        ticks[index] = 1
        yield ticks, 6, 4
        ticks = [-6] * 257
        ticks[index] = -1
        yield ticks, 6, 4
    huge = 10**400
    for magnitude in (2**53 + 1, 2**63 + 1, huge + 1):
        yield [magnitude, -magnitude, 0, magnitude], 1, 1
        yield [magnitude * 3, -magnitude * 3], 3, huge
        yield [1, -1], magnitude, magnitude
        yield [magnitude + 1, -magnitude - 1], magnitude, 1
    for source, target in product(
        (False, True, Tick(-1), Tick(0), Tick(3), *Rate), repeat=2
    ):
        for ticks in ([], [False, True], [Tick(-6), Tick(0), Tick(6)], list(Rate)):
            yield TickList(ticks), source, target
    yield [0, -6, 3, 3, 12, -3], 3, 2
    yield [3, -3], 6, 4
    yield [2, -2], 4, 6


def attack(mod: ModuleType) -> bool:
    for ticks, source, target in _cases():
        before = list(ticks)
        valid = source > 0 and target > 0
        expected = []
        if valid:
            ratios = [Fraction(int(tick) * int(target), int(source)) for tick in ticks]
            valid = all(ratio.denominator == 1 for ratio in ratios)
            expected = [ratio.numerator for ratio in ratios]
        try:
            actual = mod.rescale_ticks(ticks, source, target)
        except Exception:
            if valid or ticks != before:
                return True
        else:
            if not valid or ticks != before:
                return True
            if not isinstance(actual, list) or actual != expected:
                return True
            if any(not isinstance(value, int) for value in actual):
                return True
    return False
