from enum import Enum, IntEnum
from itertools import zip_longest
from types import ModuleType


class PlainInt(int):
    pass


class PlainFloat(float):
    pass


class IntegerChoice(IntEnum):
    NEGATIVE = -17
    ZERO = 0
    POSITIVE = 257


class MixedInteger(int, Enum):
    NEGATIVE = -33
    ZERO = 0
    POSITIVE = 513


class MixedFloat(float, Enum):
    NEGATIVE = -3.5
    ZERO = -0.0
    POSITIVE = 0.125
    INFINITY = float("inf")
    NAN = float("nan")


def _cases() -> list[tuple[int | float, str]]:
    integers = list(range(-257, 258))
    for exponent in (31, 32, 53, 63, 64, 127, 128, 1024, 14300, 20000):
        for offset in (-1, 0, 1):
            number = (1 << exponent) + offset
            integers.extend((number, -number))
    integer_cases = [(value, hex(value)) for value in integers]
    integer_cases += [(PlainInt(value), expected) for value, expected in integer_cases]
    integer_cases += [(False, "0x0"), (True, "0x1")]
    integer_cases += [(value, hex(value.value)) for value in IntegerChoice]
    integer_cases += [(value, hex(value.value)) for value in MixedInteger]
    floats = [
        0.0, -0.0, 1.0, -1.0, 0.1, -0.1, 1.5, -3.5,
        float("inf"), float("-inf"), float("nan"), -float("nan"),
    ]
    for token in (
        "0x0.0000000000001p-1022", "0x0.fffffffffffffp-1022",
        "0x1.0000000000000p-1022", "0x1.0000000000001p+0",
        "0x1.fffffffffffffp+0", "0x1.fffffffffffffp+1023",
        "0x1.0000000000001p+53", "0x1.0123456789abcp-100",
    ):
        number = float.fromhex(token)
        floats.extend((number, -number))
    float_cases = [(value, float.hex(value)) for value in floats]
    float_cases += [(PlainFloat(value), expected) for value, expected in float_cases]
    float_cases += [(value, float.hex(value.value)) for value in MixedFloat]
    cases = [
        (0, "0x0"), (1.5, "0x1.8000000000000p+0"),
        (-17, "-0x11"), (-0.0, "-0x0.0p+0"),
    ]
    for integer, real in zip_longest(integer_cases, float_cases):
        if integer is not None:
            cases.append(integer)
        if real is not None:
            cases.append(real)
    return cases


def attack(mod: ModuleType) -> bool:
    cases = _cases()
    for sequence in (cases, list(reversed(cases)), cases):
        for value, expected in sequence:
            try:
                actual = mod.numeric_token(value)
            except Exception:
                return True
            if not isinstance(actual, str) or actual != expected:
                return True
    return False
