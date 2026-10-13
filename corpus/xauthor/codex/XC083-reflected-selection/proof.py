from enum import IntEnum
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class Mark(IntEnum):
    NEGATIVE = -2
    MINUS_ONE = -1
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3


def _cases():
    yield from product(range(-2, 10), repeat=3)
    values = [
        False, True,
        *list(Mark),
        *(PlainInt(i) for i in range(-2, 4)),
        *range(-2, 4),
    ]
    yield from product(values, repeat=3)
    for size in (2**53 - 1, 2**53 + 1, 2**64, 2**200, 10**400):
        edges = (-size, -1, 0, 1, size - 1, size, size + 1)
        yield from product(edges, repeat=3)
        for args in (
            (size, 0, size), (size, 1, size - 1),
            (size, size, size), (size, 1, 1),
            (size, -1, size), (size, 0, size + 1),
            (size, size, 0),
        ):
            for position in range(3):
                typed = list(args)
                typed[position] = PlainInt(typed[position])
                yield tuple(typed)


def attack(mod: ModuleType) -> bool:
    for args in _cases():
        length, start, stop = map(int, args)
        valid = length >= 0 and 0 <= start <= stop <= length
        try:
            result = mod.reflect_selection(*args)
        except Exception:
            if valid:
                return True
            continue
        if not valid:
            return True
        if not isinstance(result, tuple) or len(result) != 2:
            return True
        if not all(isinstance(boundary, int) for boundary in result):
            return True
        left, right = result
        if not 0 <= left <= right <= length:
            return True
        if left + stop != length or right + start != length:
            return True
        if right - left != stop - start:
            return True
        if length <= 10:
            document = list(range(length))
            actual = document[::-1][left:right]
            expected = document[start:stop][::-1]
            if actual != expected:
                return True
    return False
