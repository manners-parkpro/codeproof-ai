from enum import IntEnum
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class PlainList(list):
    pass


class PlainTuple(tuple):
    pass


class Endpoint(IntEnum):
    LOW = -1
    ZERO = 0
    HIGH = 1


def cases():
    yield []
    yield [(0, 1), (1, 2)]
    yield [(0, 4), (1, 3), (2, 5)]
    yield [(3, 3)]
    yield [(0, 4), (2, 2), (2, 3)]
    yield [(-4, -2), (-3, -1)]
    yield [(2, 4), (0, 3)]
    yield [(0, 1)] * 257
    yield [(0, 1)] * 256 + [(0, 2)]
    yield [(3, 2)]
    yield [(0, 1), (3, 2)]
    yield [(3, 2), (0, 1)]
    yield [(False, True), (True, True)]
    yield [(Endpoint.LOW, Endpoint.HIGH), (Endpoint.ZERO, Endpoint.HIGH)]
    yield [(PlainInt(-1), PlainInt(2)), (PlainInt(1), PlainInt(3))]
    yield PlainList([(0, 2), (1, 3)])
    yield [PlainTuple((0, 2)), PlainTuple((1, 3))]
    yield [(True, False)]
    yield [(Endpoint.HIGH, Endpoint.LOW)]
    yield [(PlainInt(2), PlainInt(-2))]
    for origin in (2**60, -(2**60), 10**400, -(10**400)):
        yield [(origin, origin + 1), (origin + 1, origin + 2)]
        yield [(origin, origin + 3), (origin + 1, origin + 2)]
        yield [(origin, origin)]
        yield [(origin + 1, origin)]
    small = [(start, stop) for start in (-1, 0, 1) for stop in (-1, 0, 1)]
    for size in range(1, 5):
        for spans in product(small, repeat=size):
            yield list(spans)


def attack(mod: ModuleType) -> bool:
    for spans in cases():
        invalid = any(start > stop for start, stop in spans)
        expected = max(
            (sum(start <= point < stop for start, stop in spans) for point, _ in spans),
            default=0,
        )
        try:
            actual = mod.peak_concurrency(spans)
        except Exception:
            if invalid:
                continue
            return True
        if invalid or actual != expected:
            return True
    return False
