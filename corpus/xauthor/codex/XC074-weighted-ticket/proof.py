from enum import IntEnum
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class PlainList(list):
    pass


class Weight(IntEnum):
    NEGATIVE = -1
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9


def _expected(weights, ticket):
    if any(value < 0 for value in weights) or ticket < 0:
        return None
    left = 0
    selected = None
    for index, value in enumerate(weights):
        right = left + value
        if left <= ticket < right:
            selected = index
        left = right
    return selected


def _cases():
    for size in range(5):
        for weights in product(range(-1, 4), repeat=size):
            for ticket in range(-1, sum(max(w, 0) for w in weights) + 2):
                yield list(weights), ticket
    for number in (2**53 + 1, 2**63 + 1, 10**400):
        for weights in ([number, 0, 2], [1, number, 3], [0, number, number],
                        [number, -1], [-number, number + 2]):
            points = {-number, -1, 0, 1, number - 1, number, number + 1}
            total = 0
            for weight in weights:
                total += weight
                points.update((total - 1, total, total + 1))
            for ticket in sorted(points):
                yield list(weights), ticket
    for convert in (PlainInt, Weight):
        for weights in ([], [0], [0, 2, 0, 3], [2, 3, -1], [-1, 3], [3, 2, 1]):
            for ticket in range(-1, 10):
                for container in (list, PlainList):
                    yield container(convert(w) for w in weights), convert(ticket)
                    yield container(weights), convert(ticket)
                    yield container(convert(w) for w in weights), ticket
    for size in range(5):
        for weights in product((False, True), repeat=size):
            for ticket in (False, True, -1, 2, 3, 4, 5):
                yield list(weights), ticket
                yield PlainList(weights), ticket
    for size in (31, 128, 513):
        for weights in ([0] * size + [3], [1] * size, [2] + [0] * size + [1],
                        [3] + [0] * size + [-1]):
            for ticket in (-1, 0, 1, 2, 3, size - 1, size, size + 1):
                yield weights.copy(), ticket


def attack(mod: ModuleType) -> bool:
    for weights, ticket in _cases():
        before = tuple(weights)
        expected = _expected(weights, ticket)
        try:
            actual = mod.bucket_for_ticket(weights, ticket)
        except Exception:
            if expected is not None:
                return True
        else:
            if expected is None or actual != expected:
                return True
        if len(weights) != len(before):
            return True
        if any(actual is not original for actual, original in zip(weights, before)):
            return True
    return False
