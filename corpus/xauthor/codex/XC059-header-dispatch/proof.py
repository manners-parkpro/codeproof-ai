from collections import OrderedDict, defaultdict
from enum import Enum
from types import ModuleType


class HeaderList(list):
    pass


class NestedHeaderList(HeaderList):
    pass


class HeaderDict(dict):
    pass


class NestedHeaderDict(HeaderDict):
    pass


class HeaderString(str):
    pass


class HeaderPair(tuple):
    pass


class HeaderWord(str, Enum):
    KEY = "X-Mode"
    VALUE = "MiXeD"


def _snapshot(source):
    if isinstance(source, dict):
        return list(source.items())
    return list(list.__iter__(source))


def _fixtures():
    samples = [
        [],
        [("", "")],
        [("X-Single", "one")],
        [("z-last", "Z"), ("a-first", "A")],
        [("X-Tag", "one"), ("X-Tag", "two"), ("X-Tag", "one")],
        [("X-Mode", " MiXeD "), ("x-mode", ""), (" X-Space ", "a\r\nb\x00c")],
        [("한글", "값"), ("e\u0301", "é"), ("🔑", "\u202e")],
        [(HeaderString("X-Subclass"), HeaderString("VaLuE"))],
        [(HeaderWord.KEY, HeaderWord.VALUE)],
        [HeaderPair(("X-Pair", "p"))],
        [(str(i), "v" * (i % 7)) for i in range(257)],
        [(str(i), str(4097 - i)) for i in range(4097)],
        [("X-Long", "a" * 8193)],
    ]
    for pairs in samples:
        for kind in (list, HeaderList, NestedHeaderList):
            yield kind(pairs)
        for kind in (dict, HeaderDict, NestedHeaderDict, OrderedDict):
            yield kind(pairs)
        yield defaultdict(str, pairs)
    reordered = OrderedDict([("first", "1"), ("second", "2"), ("third", "3")])
    reordered.move_to_end("first")
    yield reordered
    reinserted = {"first": "1", "second": "2", "third": "3"}
    del reinserted["first"]
    reinserted["first"] = "4"
    yield reinserted


def attack(mod: ModuleType) -> bool:
    try:
        fixtures = list(_fixtures())
        for sources in (fixtures, list(reversed(fixtures)), fixtures):
            for source in sources:
                expected = _snapshot(source)
                first = mod.header_pairs(source)
                second = mod.header_pairs(source)
                for result in (first, second):
                    if not isinstance(result, list) or result != expected:
                        return True
                    if result is source or _snapshot(source) != expected:
                        return True
                if first is second:
                    return True
                first.append(("X-Appended", "result"))
                if _snapshot(source) != expected or second != expected:
                    return True
                first[0] = ("X-Replaced", "result")
                if _snapshot(source) != expected or second != expected:
                    return True
                del first[:]
                if _snapshot(source) != expected or second != expected:
                    return True
                third = mod.header_pairs(source)
                if not isinstance(third, list) or third != expected or third is second:
                    return True
                if _snapshot(source) != expected:
                    return True
                if isinstance(source, dict):
                    source["X-New-Input"] = "next"
                else:
                    source.append(("X-New-Input", "next"))
                changed = _snapshot(source)
                fourth = mod.header_pairs(source)
                if not isinstance(fourth, list) or fourth != changed:
                    return True
                if fourth is source or _snapshot(source) != changed or second != expected:
                    return True
    except Exception:
        return True
    return False
