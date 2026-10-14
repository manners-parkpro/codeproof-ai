"""압축 형식과 출력 경계를 공격한다 - 같은 내용 오라클로 양쪽 모듈을 판정한다."""

from enum import Enum
from hashlib import shake_256
from types import ModuleType
import zlib


class Wire(bytes):
    pass


def _cases():
    yield b"", None
    yield zlib.compress(b"recovery"), b"recovery"
    for size in (0, 1, 2, 31, 4095, 4096, 4097, 8192):
        for plain in (b"A" * size, shake_256(b"record").digest(size)):
            expected = plain if size <= 4096 else None
            for level in (0, 1, 6, 9):
                wire = zlib.compress(plain, level)
                yield wire, expected
                yield wire + b"\x00", None
                yield wire + zlib.compress(b"next"), None
                yield wire[:-1], None
                yield wire[:-1] + bytes([wire[-1] ^ 1]), None
    yield zlib.compress(b"Z" * 262144, 9), None
    for strategy in (
        zlib.Z_DEFAULT_STRATEGY,
        zlib.Z_FILTERED,
        zlib.Z_HUFFMAN_ONLY,
        zlib.Z_RLE,
        zlib.Z_FIXED,
    ):
        for window in (9, 15):
            for size in (0, 4096, 4097):
                plain = (bytes(range(256)) * 17)[:size]
                encoder = zlib.compressobj(wbits=window, strategy=strategy)
                wire = encoder.compress(plain) + encoder.flush()
                yield wire, plain if size <= 4096 else None
    small = zlib.compress(b"abcdef")
    for stop in range(len(small)):
        yield small[:stop], None
    for wire in (b"x", b"garbage", b"\x78\x00", b"\x00" * 32):
        yield wire, None
    for window in (-15, 31):
        encoder = zlib.compressobj(wbits=window)
        yield encoder.compress(b"foreign wrapper") + encoder.flush(), None
    encoder = zlib.compressobj(zdict=b"shared dictionary")
    yield encoder.compress(b"shared dictionary") + encoder.flush(), None
    yield zlib.compress(b"after rejection"), b"after rejection"


def _violates(mod: ModuleType, wire: bytes, expected: bytes | None) -> bool:
    original = mod._editable_record
    calls = []

    def observe(payload):
        calls.append(len(payload))
        return original(payload)

    mod._editable_record = observe
    try:
        try:
            result = mod.open_record(wire)
        except Exception:
            return expected is not None or bool(calls)
    finally:
        mod._editable_record = original
    if any(size > 4096 for size in calls):
        return True
    if expected is None:
        return True
    return (
        not isinstance(result, bytearray)
        or len(result) > 4096
        or result != expected
    )


def attack(mod: ModuleType) -> bool:
    for wire, expected in _cases():
        members = Enum("EncodedRecord", {"RECORD": wire}, type=bytes)
        for value in (wire, Wire(wire), members.RECORD):
            if _violates(mod, value, expected):
                return True
    return False
