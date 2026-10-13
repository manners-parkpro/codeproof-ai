"""주장 오라클과 할당 관측 - 실제 대형 할당 없이 상한 위반 시도를 기록한다."""

import builtins
from enum import IntEnum
from types import ModuleType


class Dimension(int):
    pass


class Preset(IntEnum):
    NEGATIVE = -1
    EMPTY = 0
    ONE = 1
    PADDED = 17
    LIMIT = 1024
    OVER = 1025
    HUGE = 10**120


class AllocationStopped(BaseException):
    pass


def cases():
    values = (-10**120, -65, -17, -16, -1, 0, 1, 2, 15, 16, 17,
              31, 32, 33, 63, 64, 65, 511, 512, 513, 600,
              1023, 1024, 1025, 16383, 16384, 16385, 65536, 10**120)
    for width in values:
        for height in values:
            yield width, height
    for width in values:
        for height in (0, 1, 513, 1025):
            yield Dimension(width), Dimension(height)
    for width in (False, True, *Preset):
        for height in (False, True, *Preset):
            yield width, height


def attack(mod: ModuleType) -> bool:
    missing = object()
    previous = {name: mod.__dict__.get(name, missing) for name in ("bytearray", "bytes")}
    attempts = []

    def observer(constructor):
        def allocate(size=0, *args, **kwargs):
            attempts.append(size)
            if not isinstance(size, int) or not 0 <= size <= 65536:
                raise AllocationStopped
            return constructor(size, *args, **kwargs)
        return allocate

    mod.bytearray = observer(builtins.bytearray)
    mod.bytes = observer(builtins.bytes)
    try:
        for width, height in cases():
            attempts.clear()
            row_bytes = 4 * int(width)
            padding = (-row_bytes) % 64
            expected = (row_bytes + padding) * int(height)
            allowed = width >= 0 and height >= 0 and expected <= 65536
            try:
                result = mod.new_frame(width, height)
            except AllocationStopped:
                return True
            except Exception:
                if allowed or attempts:
                    return True
                continue
            if not allowed or len(result) != expected:
                return True
        return False
    finally:
        for name, value in previous.items():
            if value is missing:
                mod.__dict__.pop(name, None)
            else:
                setattr(mod, name, value)
