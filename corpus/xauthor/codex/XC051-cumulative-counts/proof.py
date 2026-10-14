from enum import IntEnum
from itertools import product
from types import ModuleType


class Reading(int):
    pass


class Batch(list):
    pass


class Level(IntEnum):
    LOW = -2
    ZERO = 0
    HIGH = 3


def _violates(mod, samples, limits):
    original_samples = list(samples)
    original_limits = list(limits)
    ordered = all(
        samples[i] <= samples[j]
        for i in range(len(samples))
        for j in range(i + 1, len(samples))
    )
    expected = [sum(value <= limit for value in samples) for limit in limits]
    try:
        actual = mod.cumulative_counts(samples, limits)
    except Exception:
        return ordered or samples != original_samples or limits != original_limits
    return (
        not ordered
        or not isinstance(actual, list)
        or actual != expected
        or samples != original_samples
        or limits != original_limits
    )


def attack(mod: ModuleType) -> bool:
    for length in range(6):
        for values in product((-2, 0, 3), repeat=length):
            for limits in ([], [-3, -2, -1, 0, 1, 2, 3, 4], [3, -2, 3, 0]):
                if _violates(mod, list(values), list(limits)):
                    return True

    huge = 10**400
    cases = [
        ([-huge, -huge + 1, 0, huge - 1, huge], [huge, -huge, -huge - 1, huge + 1, 0]),
        ([2**53, 2**53 + 1, 2**53 + 2], [2**53 + 1, 2**53 - 1]),
        ([2**53 + 1, 2**53], []),
        ([1, 0], [0]),
        ([3, 1, 2], [2]),
        ([0, 2, 1, 3], [1]),
        (list(range(64)) + [62], [62, 63]),
        ([1] + list(range(64)), []),
        ([False, False, True, True], [True, False, 2, -1]),
        ([True, False], []),
        ([Level.LOW, Level.ZERO, Level.HIGH], [Level.HIGH, False, Level.LOW]),
        ([Level.HIGH, Level.ZERO], [Level.ZERO]),
        ([Reading(-2), Reading(0), Reading(3)], [Reading(3), Reading(-2)]),
        ([Reading(3), Reading(-2)], []),
        (Batch([-2, 0, 3]), Batch([3, -2, 0])),
        (Batch([3, 0, -2]), Batch([])),
    ]
    for samples, limits in cases:
        if _violates(mod, samples, limits):
            return True

    for values in ([], [-2], [-2, 0, 0, 3], [3, 0, -2]):
        shared = list(values)
        if _violates(mod, shared, shared):
            return True
    return False
