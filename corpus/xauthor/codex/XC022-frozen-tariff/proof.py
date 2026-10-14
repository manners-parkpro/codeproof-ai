from enum import IntEnum
from types import ModuleType


class PlainInt(int):
    pass


class Count(IntEnum):
    NEGATIVE = -3
    ZERO = 0
    POSITIVE = 4


UNITS = (
    -(2**256), -126, -1, 0, 1, 2, 125, 2**256,
    False, True, Count.NEGATIVE, Count.ZERO, Count.POSITIVE,
    PlainInt(-1), PlainInt(0), PlainInt(3), PlainInt(2**256),
)
VALUES = (
    0, -1, 1, 7, 125, -(2**256), 2**256,
    False, True, Count.NEGATIVE, Count.ZERO, Count.POSITIVE,
    PlainInt(-1), PlainInt(0), PlainInt(3), PlainInt(2**256),
)


def changed(mod: ModuleType) -> bool:
    for units in UNITS:
        try:
            actual = mod.quote(units)
        except Exception:
            return True
        if actual != 125 + 7 * max(0, units):
            return True
    return False


def assign(obj, field, value):
    setattr(obj, field, value)


def add(obj, field, value):
    if field == "base_cents":
        obj.base_cents += value
    else:
        obj.unit_cents += value


def subtract(obj, field, value):
    if field == "base_cents":
        obj.base_cents -= value
    else:
        obj.unit_cents -= value


def remove(obj, field, value):
    delattr(obj, field)


def attack(mod: ModuleType) -> bool:
    if changed(mod):
        return True
    for base in VALUES:
        for unit in VALUES:
            mod.Tariff(base_cents=base, unit_cents=unit)
            if changed(mod):
                return True
    for obj in (mod.TARIFF, mod.tariff()):
        for field in ("base_cents", "unit_cents"):
            for operation in (assign, add, subtract, remove):
                for value in VALUES:
                    try:
                        operation(obj, field, value)
                    except Exception:
                        pass
                    if changed(mod):
                        return True
    return False
