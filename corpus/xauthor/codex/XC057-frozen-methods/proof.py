"""공유 메서드 집합의 변경을 시도한다 - 원본과 공개 경로마다 결과 계약을 검사한다."""

from enum import Enum, StrEnum
from itertools import product
import operator
from types import ModuleType


EXPECTED = ("GET", "HEAD", "OPTIONS")


class Text(str):
    pass


class MixedText(str, Enum):
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    POST = "POST"
    EMPTY = ""


class StandardText(StrEnum):
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    POST = "POST"
    EMPTY = ""


VALUES = (
    *EXPECTED, "", "POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT",
    "get", "Get", "head", "options", " GET", "GET ", "GET\x00",
    "GÉT", "ＧＥＴ", "메서드", "X" * 16384,
    *("".join(chars) for chars in product("GET", repeat=3)),
)
PROBES = (*VALUES, *(Text(x) for x in VALUES), *MixedText, *StandardText)
MUTATION_VALUES = (
    *EXPECTED, "POST", "", "X" * 16384,
    Text("GET"), Text("POST"), *MixedText, *StandardText,
)


def broken(mod):
    try:
        if set(mod.supported_methods()) != set(EXPECTED):
            return True
        for value in PROBES:
            expected = any(value == item for item in EXPECTED)
            if mod.accepts(value) is not expected:
                return True
    except Exception:
        return True
    return False


def operations():
    for value in MUTATION_VALUES:
        yield "add", (value,)
        yield "discard", (value,)
        yield "remove", (value,)
    for values in (
        set(), {"POST"}, {"GET"}, set(EXPECTED),
        {"HEAD", "POST"}, {Text("GET"), Text("POST")},
        {MixedText.GET, MixedText.POST},
        {StandardText.GET, StandardText.POST},
        set(VALUES),
    ):
        for name in (
            "update", "intersection_update", "difference_update",
            "symmetric_difference_update",
        ):
            yield name, (values,)
    yield "pop", ()
    yield "clear", ()
    yield "update", (set(EXPECTED),)
    yield "pop", ()
    yield "pop", ()
    yield "pop", ()
    yield "pop", ()


def attempt(target, name, args):
    try:
        getattr(target, name)(*args)
    except Exception:
        pass


def mutate(mod, target):
    for name, args in operations():
        attempt(target, name, args)
        if broken(mod):
            return True
    for operation in (operator.ior, operator.iand, operator.isub, operator.ixor):
        for operand in (set(), {"POST"}, {"GET"}, set(EXPECTED)):
            try:
                result = operation(target, operand)
            except Exception:
                if broken(mod):
                    return True
                continue
            if broken(mod):
                return True
            for name, args in (
                ("add", ("POST",)), ("discard", ("GET",)),
                ("clear", ()), ("update", ({"POST"},)),
            ):
                attempt(result, name, args)
                if broken(mod):
                    return True
    for name, args in operations():
        try:
            getattr(set, name)(target, *args)
        except Exception:
            pass
        if broken(mod):
            return True
    return False


def derived(target):
    calls = (
        lambda: target.copy(),
        lambda: target.union(set()),
        lambda: target.union({"POST"}),
        lambda: target.intersection(set(EXPECTED)),
        lambda: target.difference({"GET"}),
        lambda: target.symmetric_difference({"POST"}),
        lambda: target | {"POST"},
        lambda: target & set(EXPECTED),
        lambda: target - {"GET"},
        lambda: target ^ {"POST"},
        lambda: {"POST"} | target,
        lambda: set(EXPECTED) & target,
        lambda: {"GET", "POST"} - target,
        lambda: {"POST"} ^ target,
    )
    for call in calls:
        try:
            result = call()
        except Exception:
            result = None
        yield result


def attack(mod: ModuleType) -> bool:
    if broken(mod):
        return True
    roots = (mod.BOOTSTRAP, mod.METHODS, mod.supported_methods())
    for target in roots:
        for result in derived(target):
            if broken(mod) or (result is not None and mutate(mod, result)):
                return True
        if mutate(mod, target):
            return True
    for target in (mod.BOOTSTRAP, mod.METHODS, mod.supported_methods()):
        for name, args in (
            ("clear", ()),
            ("add", (Text("POST"),)),
            ("update", (set(EXPECTED),)),
            ("remove", ("HEAD",)),
            ("add", (MixedText.HEAD,)),
            ("symmetric_difference_update", ({"GET", "POST"},)),
            ("clear", ()),
        ):
            attempt(target, name, args)
            if broken(mod):
                return True
    return broken(mod)
