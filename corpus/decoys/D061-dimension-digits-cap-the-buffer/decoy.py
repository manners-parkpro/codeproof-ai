"""썸네일 버퍼 - 크기 문자열의 자릿수가 상한을 정한다."""

import re

_DIMENSIONS = re.compile(r"([1-9][0-9]{0,2})x([1-9][0-9]{0,2})")
_CHANNELS = 4


def frame_buffer(spec: str) -> bytearray:
    match = _DIMENSIONS.fullmatch(spec)
    if match is None:
        raise ValueError(spec)
    width, height = int(match[1]), int(match[2])
    return bytearray(width * height * _CHANNELS)
