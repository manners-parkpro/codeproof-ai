"""빈 타일 만들기 - 변의 길이는 열거형이 허락한 두 값뿐이다."""

from enum import IntEnum


class Side(IntEnum):
    SMALL = 16
    LARGE = 64


_CHANNELS = 4


def blank_tile(side: int) -> bytes:
    size = Side(side)
    return bytes(size * size * _CHANNELS)
