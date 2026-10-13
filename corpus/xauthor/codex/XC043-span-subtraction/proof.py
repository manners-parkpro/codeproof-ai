"""주장 탐침 - 작은 정수의 집합 차와 큰 경계의 원자 구간을 독립 오라클로 사용한다."""

from enum import IntEnum
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class Boundary(IntEnum):
    NEGATIVE = -2
    ZERO = 0
    ONE = 1
    TWO = 2


PROBES = {
    "reversed_source": [(3, 1, 0, 2)],
    "reversed_cut": [(0, 4, 3, 1)],
    "reversed_cut_empty_source": [(2, 2, 3, 1)],
    "empty_source": [(2, 2, 0, 4), (2, 2, 2, 2)],
    "empty_cut": [(0, 5, 2, 2), (0, 5, -1, -1), (0, 5, 6, 6)],
    "touching": [(0, 5, -2, 0), (0, 5, 5, 7)],
    "full_erasure": [(0, 5, 0, 5), (0, 5, -2, 8)],
    "split": [(0, 5, 1, 4)],
    "unit_remainders": [(0, 3, 1, 2)],
    "prefix_only": [(0, 5, 2, 5)],
    "suffix_only": [(0, 5, 0, 2)],
    "outside": [(0, 5, -5, -2), (0, 5, 7, 9)],
    "clipped": [(0, 5, -2, 2), (0, 5, 3, 8)],
    "negative": [(-8, -2, -6, -4)],
    "bool": [(False, True, False, False), (0, 3, False, True)],
    "enum": [(Boundary.NEGATIVE, Boundary.TWO, Boundary.ZERO, Boundary.ONE)],
    "subclass": [(PlainInt(-3), PlainInt(4), PlainInt(-1), PlainInt(2))],
}


def expected(args: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    start, stop, cut_start, cut_stop = map(int, args)
    points = sorted(set((start, stop, cut_start, cut_stop)))
    kept = []
    for low, high in zip(points, points[1:]):
        if start <= low < stop and not cut_start <= low < cut_stop:
            if kept and kept[-1][1] == low:
                kept[-1] = (kept[-1][0], high)
            else:
                kept.append((low, high))
    return kept


def cases():
    for group in PROBES.values():
        yield from group
    yield from product(range(-3, 4), repeat=4)
    huge = 10 ** 400
    yield from product((-huge, -huge + 1, -1, 0, 1, huge - 1, huge), repeat=4)
    for args in product(range(-2, 3), repeat=4):
        for offset, scale in ((huge, 1), (-huge, 1), (0, huge)):
            yield tuple(offset + scale * value for value in args)
        yield tuple(PlainInt(value) for value in args)
    for args in product(tuple(Boundary), repeat=4):
        yield args
        for index in range(4):
            mixed = list(map(int, args))
            mixed[index] = args[index]
            yield tuple(mixed)
    yield from product((False, True), repeat=4)


def attack(mod: ModuleType) -> bool:
    for args in cases():
        start, stop, cut_start, cut_stop = args
        invalid = start > stop or cut_start > cut_stop
        try:
            actual = mod.subtract_span(*args)
        except Exception:
            if invalid:
                continue
            return True
        if invalid:
            return True
        if not isinstance(actual, list):
            return True
        if any(
            not isinstance(piece, tuple)
            or len(piece) != 2
            or any(not isinstance(value, int) for value in piece)
            for piece in actual
        ):
            return True
        if actual != expected(args):
            return True
    return False
