from enum import Enum
from itertools import product
from types import ModuleType


_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


class Text(str):
    pass


class Token(str, Enum):
    EMPTY = ""
    ONE = "/w=="
    TWO = "//8="
    THREE = "////"
    BAD_BITS = "/x=="
    BAD_CHAR = "AAAA!!!!"


def _encode(data: bytes) -> str:
    bits = "".join(format(byte, "08b") for byte in data)
    bits += "0" * (-len(bits) % 6)
    encoded = "".join(_ALPHABET[int(bits[i:i + 6], 2)] for i in range(0, len(bits), 6))
    return encoded + "=" * (-len(encoded) % 4)


def _oracle(token: str) -> bytes | None:
    core = token.rstrip("=")
    if any(char not in _ALPHABET for char in core):
        return None
    bits = "".join(format(_ALPHABET.index(char), "06b") for char in core)
    decoded = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits) - 7, 8))
    return decoded if _encode(decoded) == token else None


def _cases() -> list[str]:
    raw = [b"", bytes(range(256)), bytes(reversed(range(256)))]
    raw.extend(bytes([byte]) for byte in range(256))
    raw.extend(bytes([first, last]) for first, last in product(range(0, 256, 17), range(256)))
    raw.extend(bytes((i * 73 + 19) % 256 for i in range(size)) for size in range(3, 130))
    raw.extend([b"\x00" * 4096, b"\xff" * 4097, b"\xa5" * 4098])
    cases = [_encode(data) for data in raw]
    cases.extend(("AA==AAAA", "AAA=AAAA", "AA==AA==", "AAA=AAA=", "AAAA===="))
    for first in range(0, 64, 16):
        for bad in range(1, 16):
            for lead in _ALPHABET:
                cases.append(lead + _ALPHABET[first + bad] + "==")
    for third in range(0, 64, 4):
        for bad in range(1, 4):
            for prefix in ("AA", "//", "+/", "az", "09"):
                cases.append(prefix + _ALPHABET[third + bad] + "=")
    for size in range(7):
        for chars in product("A/=!", repeat=size):
            cases.append("".join(chars))
    for token in ("", "AA==", "AAA=", "AAAA", "/w==", "//8=", "////", "YWJjZGVmZ2g="):
        for bad in ("!", "!!!!", " ", "    ", "\t", "\t\t\t\t", "\n", "\r\n", "\r\n\r\n", "\x00", "\x7f", "-", "_", "é", "Ａ", "\u2028", "\ufeff"):
            for pos in range(len(token) + 1):
                cases.append(token[:pos] + bad + token[pos:])
        cases.extend(token + "=" * n for n in range(1, 9))
        cases.extend(token[:i] + "=" + token[i:] for i in range(len(token) + 1))
        cases.extend(token[:-n] for n in range(1, min(4, len(token)) + 1))
    return cases


def attack(mod: ModuleType) -> bool:
    cases = _cases()
    cases.extend(Text(token) for token in ("", "AA==", "AAA=", "AAAA", "AB==", "AAB=", "AAAA!!!!"))
    cases.extend(Token)
    for token in cases:
        expected = _oracle(token)
        before = token[:]
        try:
            actual = mod.decode_token(token)
        except Exception:
            if expected is not None:
                return True
        else:
            if expected is None or not isinstance(actual, bytes) or actual != expected:
                return True
        if token != before:
            return True
    return False
