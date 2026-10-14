"""본문 미리보기 반증 - 타입과 내용 및 길이 경계별로 명세 결과를 비교한다."""

from __future__ import annotations

import codecs
from enum import Enum, StrEnum
from types import ModuleType


class PlainText(str):
    pass


class PlainBytes(bytes):
    pass


class TextToken(str, Enum):
    EMPTY = ""
    SHORT = "status"
    UNICODE = "\uac00\U0001f600"
    LONG = "x" * 81


class StringToken(StrEnum):
    EMPTY = ""
    SHORT = "status"
    LONG = "\uac00" * 81


class BinaryToken(bytes, Enum):
    EMPTY = b""
    SHORT = b"status"
    INVALID = b"\xff"
    LONG = b"x" * 81


def _cases():
    for size in (0, 1, 2, 79, 80, 81, 82, 256, 4096):
        for char in ("x", "\uac00", "\U0001f600", "\x00", "\n", "\ud800"):
            text = char * size
            yield text
            yield PlainText(text)
            raw = text.encode("utf-8", errors="surrogatepass")
            yield raw
            yield PlainBytes(raw)
    for token_type in (TextToken, StringToken, BinaryToken):
        yield from token_type
    for value in range(256):
        raw = bytes([value])
        yield raw
        yield PlainBytes(raw)
    for raw in (
        b"\xe2\x82", b"\xf0\x9f\x98", b"\xed\xa0\x80", b"\xc0\xaf",
        b"\xe2(\xa1", b"\xf4\x90\x80\x80", b"\xef\xbb\xbftext",
        b"a" * 79 + b"\xf0\x9f\x98\x80z", b"\xff" * 81,
    ):
        yield raw
        yield PlainBytes(raw)
    for text in (" \tvalue\r\n", "a" * 79 + "\U0001f600z", "e\u0301" * 41):
        yield text
        yield PlainText(text)
        yield text.encode("utf-8")


def attack(mod: ModuleType) -> bool:
    for body in _cases():
        text = codecs.decode(body, "utf-8", "replace") if isinstance(body, bytes) else body
        chars = list(text)
        expected = "".join(chars[:80])
        if chars[80:]:
            expected += "..."
        try:
            actual = mod.render_preview(body)
        except Exception:
            return True
        if not isinstance(actual, str) or actual != expected:
            return True
    return False
