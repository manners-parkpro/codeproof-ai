"""태그 목록 읽기 - 개수 칸이 한 바이트라 미리 읽을 크기에 상한이 있다."""

import struct
from typing import BinaryIO

_COUNT = struct.Struct(">B")
_NAME = 16


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError("태그 목록이 중간에 끝났다")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_tags(stream: BinaryIO) -> list[str]:
    (count,) = _COUNT.unpack(_read_exact(stream, _COUNT.size))
    body = _read_exact(stream, count * _NAME)
    names = [body[i : i + _NAME] for i in range(0, len(body), _NAME)]
    return [name.rstrip(b"\x00").decode("ascii") for name in names]
