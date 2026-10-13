"""패딩 할당 주장의 반증 - 문법과 값 오라클 및 할당 진입 관찰을 함께 적용한다."""

from enum import Enum
import sys
from types import ModuleType


class Text(str):
    pass


class Field(str, Enum):
    ZERO = "0"
    ONE = "1"
    MAXIMUM = "9999"
    TOO_LARGE = "10000"
    LEADING_ZERO = "01"
    UNICODE_DIGIT = "\u0661"


def _value(text: str) -> int | None:
    if text == "0":
        return 0
    if not 1 <= len(text) <= 4 or text[0] not in "123456789":
        return None
    result = 0
    for digit in text:
        if digit not in "0123456789":
            return None
        result = result * 10 + ord(digit) - ord("0")
    return result


def _violates(mod: ModuleType, text: str) -> bool:
    expected = _value(text)
    if expected is not None:
        try:
            result = mod.reserve_padding(text)
        except Exception:
            return True
        return (
            not isinstance(result, bytearray)
            or len(result) != expected
            or any(result)
        )

    reached_allocator = False
    allocator_code = mod._allocate.__code__
    previous_profile = sys.getprofile()

    def observe(frame, event, arg):
        nonlocal reached_allocator
        if event == "call" and frame.f_code is allocator_code:
            reached_allocator = True

    sys.setprofile(observe)
    try:
        try:
            mod.reserve_padding(text)
        except Exception:
            return reached_allocator
        return True
    finally:
        sys.setprofile(previous_profile)


def attack(mod: ModuleType) -> bool:
    if _violates(mod, "10000"):
        return True

    for value in range(10000):
        if _violates(mod, str(value)):
            return True

    for value in (0, 1, 9, 10, 99, 100, 999, 1000, 9998, 9999):
        if _violates(mod, Text(str(value))):
            return True

    invalid = [
        "", "00", "01", "0000", "00000", "09999", "10000", "10001",
        "99999", "100000", "-1", "-0", "+0", "+1", "+9999",
        " 1", "1 ", "\t1", "1\t", "\n1", "1\n", "1\r\n", "1\v",
        "1\f", "1\u00a0", "\u00a01", "1\u200b", "1\u2028", "1\u2029",
        "1_0", "1_000", "0_0", "1.0", "1e3", "0x10", "a1", "1a",
        "1\x00", "\x001", "\u0661", "\uff11", "1\u0662", "\u0661\u0662",
        "\u00b2", "\U0001d7cf", "\ud800", "\udfff", "\uffff",
        "0" * 10000, "1" + "0" * 10000,
    ]
    for text in invalid:
        for variant in (text, Text(text)):
            if _violates(mod, variant):
                return True

    for variant in Field:
        if _violates(mod, variant):
            return True

    for text in ("9999", "10000", "0", "00", "1", "1\n"):
        if _violates(mod, text):
            return True
    return False
