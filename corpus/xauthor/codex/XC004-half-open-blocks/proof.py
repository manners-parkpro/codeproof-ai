"""반열린 구간 반증 - 작은 구간은 바이트별 오라클로, 큰 정수는 몫과 나머지로 검사한다."""

from enum import IntEnum
from itertools import product
from types import ModuleType


class PlainInt(int):
    pass


class Number(IntEnum):
    NEGATIVE = -1
    ZERO = 0
    ONE = 1
    TWO = 2
    SEVEN = 7
    EIGHT = 8
    NINE = 9


def _cases():
    values = (
        tuple(range(-2, 18))
        + (False, True)
        + tuple(PlainInt(v) for v in (-1, 0, 1, 2, 7, 8, 9))
        + tuple(Number)
    )
    for start, stop, size in product(values, repeat=3):
        if start < 0 or stop < start or size <= 0:
            yield (start, stop, size), None
        else:
            blocks = sorted({byte // size for byte in range(start, stop)})
            expected = range(blocks[0], blocks[-1] + 1) if blocks else range(0)
            yield (start, stop, size), expected
    for big in (2**53 + 1, 2**63, 2**127 + 3, 10**1000):
        for size in (1, 2, 7, big - 1, big, big + 1):
            for start in (0, big - 1, big, big + 1, 2 * big):
                for width in (0, 1, 2, size - 1, size, size + 1, big):
                    stop = start + width
                    first, _ = divmod(start, size)
                    end, remainder = divmod(stop, size)
                    expected = range(first, end + bool(remainder)) if width else range(0)
                    for convert in (int, PlainInt):
                        yield tuple(convert(x) for x in (start, stop, size)), expected
        for args in (
            (-big, 0, 1),
            (-big, -big, 1),
            (big, big - 1, 1),
            (0, big, -big),
            (0, big, 0),
            (big, big, 0),
            (big, big, -big),
        ):
            yield args, None


def attack(mod: ModuleType) -> bool:
    for args, expected in _cases():
        try:
            actual = mod.blocks_for_span(*args)
        except Exception:
            if expected is not None:
                return True
        else:
            if expected is None:
                return True
            if not isinstance(actual, range) or actual != expected:
                return True
    return False
