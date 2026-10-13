from __future__ import annotations

from enum import IntEnum
from itertools import product
from types import ModuleType


class OrdinaryInt(int):
    pass


class OrdinaryBuffer(bytearray):
    pass


class OrdinaryList(list):
    pass


class OrdinaryTuple(tuple):
    pass


class Number(IntEnum):
    NEGATIVE = -1
    ZERO = 0
    ONE = 1
    LAST_BYTE = 255
    TOO_LARGE = 256


def _violates(mod: ModuleType, initial: bytes, edits: list[tuple[int, int]],
              buffer_type: type = bytearray) -> bool:
    buffer = buffer_type(initial)
    valid = all(offset in range(len(initial)) and value in range(256)
                for offset, value in edits)
    expected = list(initial)
    if valid:
        for offset, value in edits:
            expected[int(offset)] = int(value)
    try:
        mod.apply_patch(buffer, edits)
    except Exception:
        return valid or bytes(buffer) != initial
    return not valid or list(buffer) != expected


def attack(mod: ModuleType) -> bool:
    for size in (0, 1, 2, 3, 17, 256, 257):
        offsets = (-10**100, -size - 1, -1, 0, 1, size - 1, size,
                   size + 1, 10**100)
        values = (-10**100, -1, 0, 1, 127, 128, 254, 255, 256, 10**100)
        for fill in (0, 255, None):
            initial = bytes((i * 73 + 19) % 256 if fill is None else fill
                            for i in range(size))
            if _violates(mod, initial, []):
                return True
            valid_prefix = [(i % size, (initial[i % size] + i + 1) % 256)
                            for i in range(33)] if size else []
            for count in (1, 2, 17, 33):
                if _violates(mod, initial, valid_prefix[:count]):
                    return True
            for offset, value in product(offsets, values):
                for position in (0, 1, 16, 33):
                    edits = valid_prefix[:position] + [(offset, value)]
                    if _violates(mod, initial, edits):
                        return True
                    if _violates(mod, initial, edits + valid_prefix[:2]):
                        return True
    offsets = (False, True, Number.NEGATIVE, Number.ZERO, Number.ONE,
               Number.TOO_LARGE, OrdinaryInt(-1), OrdinaryInt(0),
               OrdinaryInt(1), OrdinaryInt(2), OrdinaryInt(10**100))
    values = (False, True, *Number, OrdinaryInt(-1), OrdinaryInt(0),
              OrdinaryInt(255), OrdinaryInt(256), OrdinaryInt(10**100))
    for offset, value in product(offsets, values):
        for buffer_type, list_type, tuple_type in product(
                (bytearray, OrdinaryBuffer), (list, OrdinaryList),
                (tuple, OrdinaryTuple)):
            edits = list_type(tuple_type(pair) for pair in
                              ((0, 88), (offset, value), (1, 99)))
            if _violates(mod, b"ab", edits, buffer_type):
                return True
    return False
