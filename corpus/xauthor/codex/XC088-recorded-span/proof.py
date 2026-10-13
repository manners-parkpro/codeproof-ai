from enum import IntEnum
from itertools import product
from types import ModuleType


class Reading(int):
    pass


class SampleList(list):
    pass


class Code(IntEnum):
    LOW = -7
    ZERO = 0
    HIGH = 19


def _cases():
    yield []
    yield [None]
    yield [None, 3]
    yield [3, None]
    yield [0, 9]
    yield [False, 9]
    yield [True, 9]
    yield [-9, -2]
    yield [12, 12, 12]
    yield [Reading(-31), Reading(0), Reading(47), None]
    yield [Code.LOW, Code.ZERO, Code.HIGH, None]
    yield [Code.ZERO, 9]
    yield [Reading(0), 9]
    yield [-(1 << 4096), 1 << 4096, None]
    yield [1 << 4096]
    yield [1 << 100, (1 << 100) + 1]
    yield [None] * 1025
    yield [None] * 1024 + [0, 51]
    yield [4] * 1024 + [-37, 81]
    yield [81, -37] + [4] * 1024
    for size in range(5):
        yield from map(list, product((None, -2, 0, 3), repeat=size))


def _expected(samples):
    numbers = [int(value) for value in samples if value is not None]
    if not numbers:
        return None
    ordered = sorted(numbers)
    return ordered[-1] - ordered[0]


def _check(mod, samples):
    before = tuple(samples)
    expected = _expected(before)
    try:
        actual = mod.recorded_span(samples)
    except Exception:
        return True
    if len(samples) != len(before) or any(a is not b for a, b in zip(samples, before)):
        return True
    if expected is None:
        return actual is not None
    return not isinstance(actual, int) or actual != expected


def attack(mod: ModuleType) -> bool:
    cases = [container(values) for values in _cases() for container in (list, SampleList)]
    for samples in cases + list(reversed(cases)) + cases:
        if _check(mod, samples):
            return True
    shared = SampleList([None, 2, 7])
    for replacement in ([None, 2, 7], [None], [0, -19, 23], []):
        shared[:] = replacement
        if _check(mod, shared):
            return True
    return False
