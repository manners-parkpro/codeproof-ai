from collections import Counter, OrderedDict, defaultdict
from enum import Enum, IntEnum, StrEnum
from itertools import product
from types import ModuleType


class Stock(dict):
    pass


class Requests(tuple):
    pass


class Key(str):
    pass


class Count(int):
    pass


class Label(str, Enum):
    A = "a"


class Text(StrEnum):
    B = "b"


class Number(IntEnum):
    ZERO = 0
    ONE = 1
    THREE = 3


def snapshot(mapping):
    return tuple(mapping.items())


def unchanged(mapping, before):
    after = snapshot(mapping)
    return len(after) == len(before) and all(
        ak is bk and av is bv
        for (ak, av), (bk, bv) in zip(after, before)
    )


def oracle(stock, requests):
    if any(value < 0 for value in stock.values()):
        return None
    for i, (sku, quantity) in enumerate(requests):
        if quantity < 0 or sku not in stock:
            return None
        spent = sum(q for key, q in requests[: i + 1] if key == sku)
        if spent > stock[sku]:
            return None
    return {
        key: value - sum(q for sku, q in requests if sku == key)
        for key, value in stock.items()
    }


def cases():
    yield {}, ()
    yield {}, (("a", 0),)
    yield {"": 3, "\uac00": 7}, (("", 2), ("\uac00", 7))
    alphabet = (("a", -1), ("a", 0), ("a", 1), ("a", 2),
                ("b", 0), ("b", 1), ("missing", 0))
    for a, b in product((-1, 0, 1, 3), repeat=2):
        stock = {"a": a, "b": b}
        for length in range(3):
            for requests in product(alphabet, repeat=length):
                yield stock, requests
    yield {"a": 6, "b": 0}, (("a", 1), ("a", 2), ("a", 3))
    yield {"a": 6, "b": 0}, (("a", 1), ("a", 2), ("a", 4))
    yield {"a": 9, "b": 2, "c": -1}, (("a", 1),)
    yield {"a": 9, "b": 2, "c": -1}, ()
    yield {"a": 9, "b": 2}, (("a", 1), ("b", -1))
    yield {"a": 9, "b": 2}, (("a", 1), ("missing", 0))
    yield {"a": 9, "b": 2}, (("a", 1), ("b", 3))
    huge = 10 ** 200
    for value in (-huge, 0, huge):
        for quantity in (-huge, 0, huge, huge + 1):
            yield {"a": value, "b": 7}, (("a", quantity),)
    yield {"a": huge, "b": 7}, (("a", huge - 1), ("a", 1))
    yield {"a": huge, "b": 7}, (("a", huge - 1), ("a", 2))
    for factory in (Stock, OrderedDict, Counter, lambda d: defaultdict(int, d)):
        yield factory({"a": 4, "b": 7}), Requests((("a", 1), ("a", 3)))
        yield factory({"a": 4, "b": 7}), Requests((("a", 1), ("b", 8)))
    yield Stock({Key("a"): Count(5), Text.B: Number.THREE}), Requests(
        (Requests((Label.A, Number.ONE)), (Key("b"), True))
    )
    yield {Label.A: Number.THREE, Key("b"): False}, ((Key("a"), True),)
    yield {Key("a"): Count(4)}, ((Key("a"), Count(2)),)
    yield {"a": True, "b": False}, (("a", True), ("b", False))
    yield {"a": Number.ZERO}, (("a", Number.ONE),)
    yield {str(i): i for i in range(257)}, tuple((str(i), i) for i in range(257))
    yield {"a": 257, "b": 13}, (("a", 1),) * 257
    yield {"a": 257, "b": 13}, (("a", 1),) * 258


def edit(mapping, operation):
    if operation == "assign":
        mapping["a"] = 1001
    elif operation == "delete":
        del mapping["a"]
    elif operation == "insert":
        mapping["new"] = 19
    elif operation == "clear":
        mapping.clear()
    elif operation == "update":
        mapping.update({"a": 1001, "new": 19})
    elif operation == "pop":
        mapping.pop("a")
    elif operation == "setdefault":
        mapping.setdefault("new", 19)
    elif operation == "union":
        mapping |= {"a": 1001, "new": 19}
    else:
        raise RuntimeError(operation)


def isolated(mod):
    operations = ("assign", "delete", "insert", "clear", "update",
                  "pop", "setdefault", "union")
    for requests in ((), (("a", 2),), (("a", 7), ("b", 5))):
        for operation, change_source in product(operations, (False, True)):
            source = {"a": 7, "b": 5, "untouched": 11}
            before = snapshot(source)
            try:
                result = mod.preview_reservations(source, requests)
            except Exception:
                return False
            if not unchanged(source, before) or result != oracle(source, requests):
                return False
            target, observer = (source, result) if change_source else (result, source)
            observed = snapshot(observer)
            try:
                edit(target, operation)
            except Exception:
                return False
            if not unchanged(observer, observed):
                return False
    return True


def attack(mod: ModuleType) -> bool:
    for template, requests in cases():
        source = template.copy()
        if isinstance(template, Stock):
            source = Stock(source)
        before = snapshot(source)
        expected = oracle(source, requests)
        try:
            result = mod.preview_reservations(source, requests)
        except Exception:
            if expected is not None or not unchanged(source, before):
                return True
        else:
            if expected is None or not unchanged(source, before):
                return True
            if result != expected:
                return True
    return not isolated(mod)
