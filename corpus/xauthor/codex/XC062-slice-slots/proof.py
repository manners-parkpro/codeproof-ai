"""슬롯 범위 반증 - 실제 슬롯 목록의 슬라이싱을 독립 오라클로 비교한다."""

from collections.abc import Sequence
from enum import IntEnum, IntFlag
from itertools import product
from types import ModuleType


class SlotInt(int):
    pass


class ChildSlotInt(SlotInt):
    pass


class SlotEnum(IntEnum):
    LOW = -257
    BACK = -1
    ZERO = 0
    ONE = 1
    TWO = 2
    LAST = 255
    END = 256
    HIGH = 257


class SlotFlag(IntFlag):
    ZERO = 0
    ONE = 1
    TWO = 2
    END = 256


def _violates(mod: ModuleType, args: tuple[int, ...]) -> bool:
    step = args[2] if len(args) == 3 else 1
    expected = tuple(range(256))[slice(args[0], args[1], step)] if step else None
    try:
        actual = mod.select_slots(*args)
    except Exception:
        return step != 0
    if step == 0 or not isinstance(actual, Sequence):
        return True
    return len(actual) > 256 or tuple(actual) != expected


def attack(mod: ModuleType) -> bool:
    cases = [
        (0, 1024, 1),
        (255, -257, -1),
        (0, 256, 0),
        (0, 256, 1),
        (0, 0, 1),
        (-256, 256, 1),
        (0, 256, 1),
        (256, 0, -1),
        (0, 256),
    ]
    for args in cases * 3:
        if _violates(mod, args):
            return True
    edges = (-1024, -513, -257, -256, -255, -2, -1, 0, 1, 2, 254, 255, 256, 257, 513, 1024)
    strides = (-1025, -257, -256, -255, -7, -2, -1, 0, 1, 2, 7, 255, 256, 257, 1025)
    for args in product(edges, edges, strides):
        if _violates(mod, args):
            return True
    for pos in range(-257, 258):
        for args in ((pos, pos + 1, 1), (pos, pos - 1, -1), (pos, pos, 2)):
            if _violates(mod, args):
                return True
    for power in (63, 64, 127, 1024, 4096):
        huge = 1 << power
        cases = [
            (huge, huge + 513, 1),
            (-huge, -huge + 513, 1),
            (huge + 513, huge, -1),
            (-huge + 513, -huge, -1),
            (0, 256, huge),
            (255, -257, -huge),
            (-huge, huge, huge),
            (huge, -huge, -huge),
        ]
        for args in cases:
            if _violates(mod, args):
                return True
    constructors = (int, SlotInt, ChildSlotInt, SlotEnum, SlotFlag)
    for kinds in product(constructors, repeat=3):
        for raw in ((-257, 257, 1), (255, -257, -1), (0, 256, 2), (0, 256, 0)):
            args = tuple(kind(value) for kind, value in zip(kinds, raw))
            if _violates(mod, args):
                return True
    for flag in (False, True):
        for args in ((flag, 256, 1), (0, flag, 1), (0, 256, flag)):
            if _violates(mod, args):
                return True
    return False
