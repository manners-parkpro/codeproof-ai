"""RGB 계약 반증 - 독립적인 문자 검사와 자리값 계산으로 결과를 비교한다."""

from enum import Enum
from types import ModuleType


class Text(str):
    pass


class Color(str, Enum):
    PREFIXED = "#12aB00"
    BARE = "aB01fF"
    EMPTY = ""
    INVALID = "red"
    ENDLINE = "123456\n"


def expected(text: str) -> tuple[int, int, int] | None:
    body = text[1:] if text.startswith("#") else text
    digits = "0123456789abcdef"
    if len(body) != 6 or any(char not in digits + "ABCDEF" for char in body):
        return None
    values = [digits.index(char.lower()) for char in body]
    return (
        values[0] * 16 + values[1],
        values[2] * 16 + values[3],
        values[4] * 16 + values[5],
    )


def samples() -> list[str]:
    cases = [
        "", "#", "000000", "#FFFFFF", "123456", "#12aBef", "aBcDeF",
        "##123456", "0x123456", "123456#", "+123456", "-123456",
        "# 123456", "12 456", "123456\n", "123456\r\n", "123456\x00",
        "\n123456", " 123456", "123456 ", "junk123456junk", "#123456#",
        "１２３４５６", "١٢٣٤٥٦", "ABCＤEF", "\ud80012345",
        "000000" * 20000, "#" + "f" * 120000,
    ]
    for length in range(16):
        cases.extend(("1" * length, "#" + "1" * length))
    for channel in range(3):
        for value in range(256):
            channels = [0x19, 0xA7, 0xE3]
            channels[channel] = value
            body = "".join(format(item, "02x") for item in channels)
            cases.extend((body, "#" + body.upper()))
    for position in range(6):
        for char in map(chr, range(128)):
            body = "1aB4eF"
            changed = body[:position] + char + body[position + 1:]
            cases.extend((changed, "#" + changed))
        for char in ("\u00a0", "\u200b", "\u2028", "\u2029", "\uff11", "\u0661", "\udfff"):
            body = "123456"
            cases.append(body[:position] + char + body[position + 1:])
    for char in ("\t", "\n", "\r", "\v", "\f", " ", "\x00", "\u0085", "\u2028", "\u2029"):
        cases.extend((char + "123456", "123456" + char))
    return cases


def attack(mod: ModuleType) -> bool:
    cases = samples()
    inputs = cases + [Text(value) for value in cases] + list(Color)
    inputs.extend(["#12aBef", "bad", "000000", "#FFFFFF", ""] * 3)
    for text in inputs + list(reversed(inputs)):
        wanted = expected(text)
        try:
            actual = mod.parse_rgb(text)
        except Exception:
            return True
        if wanted is None:
            if actual is not None:
                return True
        elif not isinstance(actual, tuple) or actual != wanted:
            return True
        elif any(not isinstance(channel, int) for channel in actual):
            return True
    return False
