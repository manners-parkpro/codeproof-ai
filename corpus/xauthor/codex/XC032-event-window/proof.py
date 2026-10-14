"""시간창 계약 반증 - 이진 탐색과 독립적인 선형 선택으로 모든 결과를 대조한다."""

from enum import IntEnum
from itertools import product
from types import ModuleType


class Tick(int):
    pass


class TickList(list):
    pass


class NamedTick(IntEnum):
    LOW = -2
    NEGATIVE = -1
    ZERO = 0
    ONE = 1
    HIGH = 2


def cases():
    for length in range(5):
        for values in product(range(-2, 3), repeat=length):
            for start, stop in product(range(-3, 4), repeat=2):
                yield list(values), start, stop
    for base in (-10**400, -(2**63), -(2**53), 2**53, 2**63, 10**400):
        values = [base - 2, base - 1, base, base, base + 1, base + 2]
        for start, stop in product(range(-3, 4), repeat=2):
            yield values, base + start, base + stop
        yield values[::-1], base - 3, base + 3
    for convert in (Tick, NamedTick, bool):
        values = sorted(convert(x) for x in (-2, -1, 0, 0, 1, 2))
        for container in (list, TickList):
            for start, stop in product(range(-2, 3), repeat=2):
                yield container(values), convert(start), convert(stop)
                yield container(values), start, stop
            yield container(), convert(1), convert(0)
            yield container(values[::-1]), convert(-2), convert(2)
    mixed = [NamedTick.LOW, Tick(-1), False, NamedTick.ZERO, True, Tick(2)]
    for start, stop in product(range(-3, 4), repeat=2):
        yield TickList(mixed), start, stop
    for size in (1, 2, 17, 256, 257, 1025):
        values = list(range(-size, size))
        yield values, -size, size
        yield values, -size + 1, size - 1
        yield values, size + 1, size + 2
        yield values, -size - 2, -size - 1
        yield [0] * size, -1, 1
        yield [0] * size, 0, 0
        yield [0] * size, 0, 1
        yield [0] * size, -1, 0
        if size > 1:
            for index in (0, size - 1, len(values) - 2):
                unordered = values.copy()
                unordered[index], unordered[index + 1] = unordered[index + 1], unordered[index]
                yield unordered, -size, size
    yield [0, 1], -10**400, 10**400
    yield [], -10**400, 10**400
    yield [], 10**400, -10**400


def attack(mod: ModuleType) -> bool:
    for raw, start, stop in cases():
        ticks = type(raw)(raw)
        before = list(ticks)
        invalid = start > stop or any(
            before[i] > before[i + 1] for i in range(len(before) - 1)
        )
        expected = [t for t in before if start <= t < stop]
        try:
            actual = mod.events_between(ticks, start, stop)
        except Exception:
            if ticks != before or not invalid:
                return True
        else:
            if ticks != before or invalid:
                return True
            if not isinstance(actual, list) or actual != expected:
                return True
    return False
