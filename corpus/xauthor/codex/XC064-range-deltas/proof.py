"""구간 갱신 반증 - 칸별 정의와 입력 스냅샷으로 결과와 거절을 검사한다."""

from enum import IntEnum
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class PlainList(list):
    pass


class PlainTuple(tuple):
    pass


class Level(IntEnum):
    NEGATIVE = -1
    ZERO = 0
    ONE = 1
    TWO = 2
    FOUR = 4


def _violates(mod, values, updates):
    before_values = list(values)
    before_updates = list(updates)
    count = len(before_values)
    valid = all(
        0 <= int(start) <= int(stop) <= count
        for start, stop, amount in before_updates
    )
    expected = [
        int(value) + sum(
            int(amount) for start, stop, amount in before_updates
            if int(start) <= index < int(stop)
        )
        for index, value in enumerate(before_values)
    ]
    try:
        actual = mod.add_ranges(values, updates)
    except Exception:
        failed = valid
    else:
        failed = not valid or not isinstance(actual, list) or actual != expected
    return (
        failed
        or values != before_values
        or updates != before_updates
        or any(a is not b for a, b in zip(values, before_values))
        or any(a is not b for a, b in zip(updates, before_updates))
    )


def _cases():
    yield [10, 20, 30, 40], [(1, 3, 7)]
    yield [5, 6, 7], [(1, 1, 11)]
    yield [], []
    yield [], [(0, 0, 10**120)]
    for size in range(5):
        values = [(-1)**index * (index + 3) for index in range(size)]
        yield values[:], []
        spans = list(product(range(size + 1), range(size + 1), (-3, 0, 2)))
        for span in spans:
            yield values[:], [span]
        valid_spans = [span for span in spans if span[0] <= span[1]]
        for first, second in product(valid_spans, repeat=2):
            yield values[:], [first, second]
        invalid = [
            (-1, 0, 2), (-1, size, 0), (0, size + 1, 2),
            (size + 1, size + 1, 0), (1, 0, 4),
            (0, -1, 4), (-10**120, 0, 4), (0, 10**120, 4),
        ]
        for bad in invalid:
            for position in range(3):
                updates = [(0, size, 6), (0, 0, -2)]
                updates.insert(position, bad)
                yield values[:], updates
    big = 10**120
    yield [big, -big, 0, big + 1], [(0, 4, big), (1, 3, -2 * big)]
    yield [3, -8, 12, 1], [(0, 4, 0), (1, 3, 9), (1, 3, -9)]
    yield list(range(257)), [(0, 257, 1), (128, 256, -7), (256, 257, big)]
    for scalar in (PlainInt, Level, bool):
        yield [scalar(0), scalar(1)], [
            (scalar(0), scalar(1), scalar(1)),
            (scalar(1), scalar(1), scalar(1)),
        ]
    yield [Level.NEGATIVE, Level.FOUR, PlainInt(big), False], [
        (Level.ZERO, Level.FOUR, Level.NEGATIVE),
        (PlainInt(1), PlainInt(3), PlainInt(-big)),
        (False, True, True),
    ]
    yield [1, 2], [(Level.NEGATIVE, Level.ONE, Level.ONE)]
    yield [1, 2], [(PlainInt(0), PlainInt(3), PlainInt(1))]
    yield PlainList([1, -2, 3]), PlainList([
        PlainTuple((0, 2, 4)), PlainTuple((2, 3, -1))
    ])
    yield PlainList([1, 2]), PlainList([PlainTuple((1, 0, 3))])
    yield [7, -4, 9], [(2, 3, 1), (0, 2, -2), (1, 3, 5), (0, 2, -2)]
    yield [1, 2, 3], [(0, 3, 1)] * 97
    yield [4, 5, 6], []
    yield [8, 9], [(0, 1, 3)]
    yield [8, 9], [(0, 1, 3)]


def attack(mod: ModuleType) -> bool:
    for values, updates in _cases():
        if _violates(mod, values, updates):
            return True
    return False
