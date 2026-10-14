"""기능 조합 버퍼 반증 - 산술 오라클로 각 계약 축을 확인한다."""

from enum import IntEnum, IntFlag
from types import ModuleType


class PlainInt(int):
    pass


class FeatureNumber(IntEnum):
    NEGATIVE = -1
    EMPTY = 0
    FIRST = 1
    SUPPORTED = 4095
    EXTENDED = 8191


class FeatureFlags(IntFlag):
    EMPTY = 0
    FIRST = 1
    LAST = 2048
    UNKNOWN = 4096


def _expected_size(value: int) -> int:
    residue = int(value) % 4096
    size = 1
    for _ in range(12):
        residue, digit = divmod(residue, 2)
        if digit:
            size *= 2
    return size


def _probes() -> list[int]:
    values = [8191, 0, 4095, -1, 1, 4096, -4096, -4097]
    for low in range(4096):
        values.extend((low, ~low))
    for bit in (12, 13, 31, 63, 64, 127, 1024, 10000):
        for low in (0, 1, 5, 2048, 4095):
            magnitude = (1 << bit) + low
            values.extend((magnitude, -magnitude))
    values.extend((False, True))
    values.extend(FeatureNumber.__members__.values())
    values.extend(FeatureFlags.__members__.values())
    values.extend(FeatureFlags(4097) for _ in range(2))
    values.extend(PlainInt(value) for value in (0, 1, -1, 4095, 8191))
    values.extend((5, 0, 4095, 5, -1, 0, 8191, 4095))
    return values


def attack(mod: ModuleType) -> bool:
    retained = []
    identities = set()
    for value in _probes():
        expected = _expected_size(value)
        try:
            result = mod.combination_buffer(value)
        except Exception:
            return True
        if not isinstance(result, bytearray):
            return True
        if len(result) != expected or not 1 <= len(result) <= 4096:
            return True
        if any(result) or id(result) in identities:
            return True
        identities.add(id(result))
        retained.append(result)
        result[:] = b"\xa5"
        result.append(90)
    return False
