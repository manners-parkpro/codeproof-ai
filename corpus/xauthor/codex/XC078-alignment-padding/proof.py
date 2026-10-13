"""정렬 재시도 반증 - 산술 오라클로 상태와 콜백 중 관측을 검사한다."""

from enum import IntEnum, IntFlag
from types import ModuleType


class PlainInt(int):
    pass


class Number(IntEnum):
    NEGATIVE = -7
    ZERO = 0
    ONE = 1
    SEVEN = 7
    EIGHT = 8


class Bits(IntFlag):
    ZERO = 0
    ONE = 1
    TWO = 2
    EIGHT = 8


def attack(mod: ModuleType) -> bool:
    huge = 10**120
    integers = [
        -huge, -17, -1, 0, 1, 2, 3, 7, 8, 9, 15, 16, 17,
        255, 256, 257, huge - 1, huge, huge + 1,
        False, True, PlainInt(-7), PlainInt(0), PlainInt(9),
        Number.NEGATIVE, Number.ZERO, Number.ONE, Number.SEVEN,
        Number.EIGHT, Bits.ZERO, Bits.ONE, Bits.TWO | Bits.EIGHT,
    ]
    attempts_values = [
        -huge, -3, -1, 0, 1, 2, 5, False, True,
        PlainInt(-2), PlainInt(0), PlainInt(3), Number.NEGATIVE,
        Number.ZERO, Number.ONE, Number.SEVEN, Bits.ZERO,
        Bits.ONE, Bits.TWO | Bits.EIGHT,
    ]

    def create(initial):
        try:
            obj = mod.AllocationSize(initial)
        except BaseException:
            return None, int(initial) >= 0
        if int(initial) < 0:
            return None, True
        try:
            return obj, obj.snapshot() != int(initial)
        except BaseException:
            return None, True

    def step(obj, before, quantum, attempts, mode):
        q = int(quantum)
        expected = before
        if q > 0 and int(attempts) > 0:
            expected = -(-before // q) * q
        mismatch = False
        calls = 0

        def acknowledge():
            nonlocal mismatch, calls
            calls += 1
            try:
                mismatch |= obj.snapshot() != expected
            except BaseException:
                mismatch = True
            if mode == "timeout" or (mode == "recover" and calls <= 2):
                raise TimeoutError("lost reply")
            if mode == "fatal":
                raise RuntimeError("peer failed")
            if mode == "interrupt":
                raise KeyboardInterrupt("synchronous callback exception")
            if mode == "late_fatal":
                if calls == 1:
                    raise TimeoutError("lost reply")
                raise ValueError("peer rejected")
            return object()

        try:
            obj.align(quantum, acknowledge, attempts)
        except BaseException:
            pass
        try:
            return mismatch or obj.snapshot() != expected, expected
        except BaseException:
            return True, expected

    for initial in integers:
        _, broken = create(initial)
        if broken:
            return True

    obj, broken = create(5)
    if broken:
        return True
    broken, _ = step(obj, 5, 8, 3, "recover")
    if broken:
        return True

    modes = ["success", "timeout", "recover", "fatal", "late_fatal", "interrupt"]
    for initial in integers:
        if int(initial) < 0:
            continue
        for quantum in integers:
            for attempts in attempts_values:
                for mode in modes:
                    obj, broken = create(initial)
                    if broken:
                        return True
                    broken, _ = step(obj, int(initial), quantum, attempts, mode)
                    if broken:
                        return True

    for initial in [0, 1, 7, 64, huge + 3]:
        obj, broken = create(initial)
        if broken:
            return True
        expected = initial
        for quantum, attempts, mode in [
            (8, 3, "timeout"), (8, 5, "recover"), (3, 1, "fatal"),
            (3, 2, "timeout"), (7, 0, "success"), (7, -2, "timeout"),
            (0, 2, "success"), (-1, 3, "fatal"), (5, 3, "late_fatal"),
            (16, 4, "recover"), (1, 1, "success"), (huge, 2, "timeout"),
            (PlainInt(9), Number.SEVEN, "recover"), (Bits.EIGHT, True, "fatal"),
            (huge + 1, huge, "success"), (3, huge, "fatal"),
            (11, 8, "interrupt"), (11, 3, "timeout"),
        ]:
            broken, expected = step(obj, expected, quantum, attempts, mode)
            if broken:
                return True
    return False
