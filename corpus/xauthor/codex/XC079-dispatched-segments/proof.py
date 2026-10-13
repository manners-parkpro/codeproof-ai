"""경로 분해 계약 반증 - 내용 오라클과 반환 목록 변경으로 타입별 경계를 시험한다."""

from collections import namedtuple
from enum import Enum
from itertools import product
from types import ModuleType


class Text(str):
    pass


class MoreText(Text):
    pass


class Parts(tuple):
    pass


class MoreParts(Parts):
    pass


class TextKind(str, Enum):
    EMPTY = ""
    PATH = "/A//b/"
    UNICODE = "가/é/e\u0301/\ud800/\x00"


class PartsKind(tuple, Enum):
    EMPTY = ()
    PATH = ("a/b", "", "a/b")
    UNICODE = ("가", "é", "e\u0301", "\ud800")


def _expected(value):
    if isinstance(value, str):
        text = str.__str__(value)
        pieces = []
        start = 0
        for offset, character in enumerate(text):
            if character == "/":
                pieces.append(text[start:offset])
                start = offset + 1
        pieces.append(text[start:])
        return pieces
    return [part for part in value]


def _cases():
    texts = ["", "a", "/", "//", "/a", "a/", "z/a/z", " A / b "]
    texts += ["가/é/e\u0301", "a\\b", "a\u2215b\uff0fc", "\x00/\r\n/\t", "\ud800/\udfff"]
    texts += ["x" * 8192, "/" * 4097, "left/" + "m" * 8192 + "/right"]
    for size in range(4):
        texts.extend("".join(chars) for chars in product("aA/ ", repeat=size))
    values = []
    for text in texts:
        values.extend((text, Text(text), MoreText(text)))
    values.extend(TextKind)
    tuples = [(), ("",), ("/",), ("a/b", "c//d"), ("z", "a", "z"), (" A ", "b")]
    tuples += [("가", "é", "e\u0301", "\ud800", "\x00"), (Text("a/b"), TextKind.PATH, TextKind.EMPTY)]
    tuples += [("",) * 4097, ("tail",) * 4096 + ("end",)]
    for size in range(4):
        tuples.extend(product(("", "/", "a", "A", " b "), repeat=size))
    for parts in tuples:
        values.extend((parts, Parts(parts), MoreParts(parts)))
    values.extend(PartsKind)
    pair_type = namedtuple("Pair", "left right")
    empty_type = namedtuple("Empty", "")
    values.extend((pair_type("a/b", ""), pair_type(TextKind.PATH, Text("가")), empty_type()))
    return values


def attack(mod: ModuleType) -> bool:
    values = _cases()
    retained = []
    changes = (
        lambda parts: parts.append("added"),
        lambda parts: parts.__delitem__(slice(None)),
        lambda parts: parts.__setitem__(slice(None), ["replaced"]),
        lambda parts: parts.sort(reverse=True),
    )
    try:
        for sequence in (values, list(reversed(values))):
            for value in sequence:
                expected = _expected(value)
                first = mod.path_segments(value)
                if not isinstance(first, list) or first != expected:
                    return True
                if not all(isinstance(part, str) for part in first):
                    return True
                retained.append((first, expected))
                for change in changes:
                    editable = mod.path_segments(value)
                    if editable is first or editable != expected:
                        return True
                    change(editable)
                    fresh = mod.path_segments(value)
                    if fresh is editable or fresh is first or fresh != expected:
                        return True
                    if first != expected or _expected(value) != expected:
                        return True
        return any(result != expected for result, expected in retained)
    except Exception:
        return True
