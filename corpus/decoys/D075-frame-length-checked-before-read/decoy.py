"""프레임 읽기 - 머리의 길이를 본문을 읽기 전에 상한과 견준다."""

import struct
from typing import BinaryIO

_MAX_FRAME = 64 * 1024


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            break
        data += chunk
    return bytes(data)


def read_frame(stream: BinaryIO) -> bytes:
    header = _read_exact(stream, 4)
    if len(header) != 4:
        raise ValueError("머리가 잘렸다")
    (length,) = struct.unpack(">I", header)
    if length > _MAX_FRAME:
        raise ValueError(f"프레임이 너무 크다: {length}")
    body = _read_exact(stream, length)
    if len(body) != length:
        raise ValueError("본문이 잘렸다")
    return body
