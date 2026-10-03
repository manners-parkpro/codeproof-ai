"""파일 머리 쓰기 - 나눠 주는 머리는 받은 쪽이 고칠 수 없는 bytes 다."""

from typing import BinaryIO

_MAGIC = b"CPRF"
_HEADER = _MAGIC + bytes([1, 0])


def header() -> bytes:
    return _HEADER


def write(stream: BinaryIO, payload: bytes) -> None:
    stream.write(header())
    stream.write(len(payload).to_bytes(4, "big"))
    stream.write(payload)
