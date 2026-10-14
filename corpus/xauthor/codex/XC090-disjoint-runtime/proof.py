from enum import IntEnum
from itertools import combinations, permutations, product
from types import ModuleType


class Coordinate(int):
    pass


class Tick(IntEnum):
    BEFORE = -3
    START = 0
    STOP = 4


class Intervals(list):
    pass


class Interval(tuple):
    pass


PROBES = {
    "empty": [],
    "reversed": [(5, 2)],
    "later reversed": [(0, 1), (9, 3)],
    "negative reversed": [(-2, -5)],
    "crossing": [(0, 5), (3, 8)],
    "nested": [(0, 10), (3, 7)],
    "duplicate": [(1, 8), (1, 8)],
    "late overlap": [(0, 1), (2, 8), (4, 6)],
    "unit overlap": [(0, 3), (2, 5)],
    "negative overlap": [(-8, -3), (-5, -1)],
    "unsorted disjoint": [(8, 11), (0, 3), (5, 6)],
    "touching": [(-3, 0), (0, 4), (4, 9)],
    "zero inside": [(1, 7), (4, 4)],
    "all zero": [(8, 8), (-1, -1), (8, 8)],
    "zero boundary": [(1, 1), (1, 7), (7, 7)],
    "zero obscures overlap": [(0, 10), (4, 4), (5, 8)],
    "gap": [(-9, -5), (8, 12)],
    "nonzero origin": [(81, 86)],
    "negative origin": [(-83, -79)],
    "large positive": [(2**100, 2**100 + 7)],
    "large negative": [(-2**100 - 11, -2**100)],
    "huge": [(-10**400, -10**400 + 2), (10**400, 10**400 + 3)],
    "huge reverse": [(10**400 + 1, 10**400)],
    "huge overlap": [(10**400, 10**400 + 3), (10**400 + 1, 10**400 + 8)],
    "bool": [(False, True)],
    "bool reverse": [(True, False)],
    "bool collision": [(False, True), (0, 1)],
    "enum": [(Tick.BEFORE, Tick.START), (Tick.START, Tick.STOP)],
    "enum overlap": [(Tick.BEFORE, Tick.STOP), (0, 1)],
    "int subclass": [(Coordinate(-4), Coordinate(-1)), (Coordinate(0), Coordinate(5))],
    "int subclass reverse": [(Coordinate(4), Coordinate(1))],
    "int subclass overlap": [(Coordinate(-4), Coordinate(1)), (Coordinate(0), Coordinate(5))],
    "many": [(3 * i, 3 * i + 2) for i in reversed(range(80))],
    "late reversed in many": [(3 * i, 3 * i + 2) for i in range(80)] + [(900, 899)],
    "late overlap in many": [(3 * i, 3 * i + 2) for i in range(80)] + [(238, 241)],
}


def _oracle(intervals):
    if any(start > end for start, end in intervals):
        return None
    for (a, b), (c, d) in combinations(intervals, 2):
        if max(a, c) < min(b, d):
            return None
    endpoints = sorted({point for interval in intervals for point in interval})
    total = 0
    for left, right in zip(endpoints, endpoints[1:]):
        if any(start <= left and right <= end for start, end in intervals):
            total += right - left
    return total


def _cases():
    for case in PROBES.values():
        yield list(case)
        yield Intervals(Interval(pair) for pair in case)
    for case in (
        [(0, 3), (3, 5), (9, 11)],
        [(0, 8), (2, 6), (9, 11)],
        [(0, 8), (4, 4), (9, 11)],
    ):
        for ordering in permutations(case):
            yield list(ordering)
    intervals = list(product(range(-2, 3), repeat=2))
    for size in range(4):
        for case in product(intervals, repeat=size):
            yield list(case)


def _violates(mod, intervals):
    expected = _oracle(intervals)
    before = tuple(intervals)
    rejected = False
    try:
        actual = mod.occupied_ticks(intervals)
    except Exception:
        rejected = True
    if len(intervals) != len(before):
        return True
    if any(current is not original for current, original in zip(intervals, before)):
        return True
    if expected is None:
        return not rejected
    if rejected:
        return True
    return not isinstance(actual, int) or actual != expected


def attack(mod: ModuleType) -> bool:
    return any(_violates(mod, intervals) for intervals in _cases())
