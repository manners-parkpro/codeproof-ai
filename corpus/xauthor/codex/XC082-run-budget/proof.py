"""복원 주장 반증 - 독립 오라클과 제한된 할당 관찰로 경계 및 호출 간 독립성을 검사한다."""

from builtins import bytearray as real_bytearray
from enum import IntEnum
from itertools import islice
from types import ModuleType


class PlainInt(int):
    pass


class PlainList(list):
    pass


class PlainTuple(tuple):
    pass


class Number(IntEnum):
    ZERO = 0
    ONE = 1
    LAST = 255
    LIMIT = 4096
    OVER = 4097


class AllocationLimit(Exception):
    pass


def _expected(runs):
    if any(not 0 <= value <= 255 or count < 0 for value, count in runs):
        return None
    size = sum(int(count) for _, count in runs)
    if size > 4096:
        return None
    result = []
    for value, count in runs:
        result.extend([int(value)] * int(count))
    return bytes(result)


def _cases():
    yield []
    yield [(65, 4097)]
    yield [(10, 2048), (20, 2049)]
    yield [(7, 1)] * 4097
    for size in (0, 1, 2, 4095, 4096):
        yield [(0, size)]
        yield [(255, size)]
    yield [(9, 0)] * 10000
    yield [(10, 2048), (20, 2048)]
    yield [(7, 1)] * 4096
    yield [(10, 4095), (99, 0), (20, 1), (88, 0)]
    yield [(3, 0), (2, 3), (255, 2), (1, 1), (0, 2)]
    for value in (-1, 256, -(1 << 200), 1 << 200):
        for count in (0, 1):
            yield [(value, count)]
            yield [(12, 4096), (value, count)]
    for count in (-1, -4096, -(1 << 200)):
        yield [(65, count)]
        yield [(65, count), (66, 4097)]
        yield [(65, 4096), (66, count)]
    yield [(0, 1 << 200)]
    yield [(1, 4096), (2, 1 << 200)]
    for wrapper in (int, PlainInt, Number):
        yield [(wrapper(0), wrapper(0)), (wrapper(255), wrapper(4096))]
        yield [(wrapper(1), wrapper(4097))]
    yield [(False, True), (True, False), (True, True)]
    yield PlainList([PlainTuple((PlainInt(255), PlainInt(4096)))])
    yield PlainList([PlainTuple((PlainInt(255), PlainInt(4097)))])
    for value in (0, 1, 127, 254, 255):
        for first in (0, 1, 2048, 4095, 4096):
            for second in (0, 1, 4096 - first, 4097 - first):
                yield [(value, first), (255 - value, second)]


def attack(mod: ModuleType) -> bool:
    overflow = [False]

    def bounded_bytearray(source=b""):
        if isinstance(source, int):
            if source > 4096:
                overflow[0] = True
                raise AllocationLimit
            return real_bytearray(source)
        prefix = list(islice(iter(source), 4097))
        if len(prefix) > 4096:
            overflow[0] = True
            raise AllocationLimit
        return real_bytearray(prefix)

    missing = object()
    original = mod.__dict__.get("bytearray", missing)
    mod.bytearray = bounded_bytearray
    try:
        for runs in _cases():
            snapshot = list(runs)
            expected = _expected(snapshot)
            previous = None
            for repetition in range(2):
                overflow[0] = False
                try:
                    result = mod.decode_runs(runs)
                except Exception:
                    if overflow[0] or expected is not None or runs != snapshot:
                        return True
                    continue
                if overflow[0] or expected is None or runs != snapshot:
                    return True
                if not isinstance(result, real_bytearray) or bytes(result) != expected:
                    return True
                if result is previous:
                    return True
                previous = result
                result[:] = b"changed"
        return False
    finally:
        if original is missing:
            del mod.bytearray
        else:
            mod.bytearray = original
