"""난수 배치 반증 - 상태 복원과 양방향 독립성을 입력 축별로 검사한다."""

from enum import Enum
from random import Random, SystemRandom
from types import ModuleType


class PlainRandom(Random):
    pass


class PlainTuple(tuple):
    pass


class PlainString(str):
    pass


class Label(str, Enum):
    FIRST = "first"
    SECOND = "second"


def _states():
    for seed in (0, 1, -1, 2**521 + 17, "서울", b"\x00\xff"):
        for advances in (0, 1, 623, 624, 625):
            rng = Random(seed)
            for _ in range(advances):
                rng.getrandbits(32)
            yield rng.getstate()
    for cached in (0.0, -0.0, 2.75, -1e308, float("inf"), float("nan")):
        rng = Random(713)
        rng.gauss(0.0, 1.0)
        version, internal, _ = rng.getstate()
        rng.setstate((version, internal, cached))
        yield rng.getstate()


def _entries():
    yield ()
    yield ("only",)
    yield ("left", "right")
    yield ("same", "same", "other", "same")
    yield ("", "\x00", "\n", "서울", "\U0001f600")
    yield (PlainString("first"), Label.FIRST, Label.SECOND, "first")
    for size in (3, 17, 255, 256, 257, 1025):
        yield tuple(str(i) for i in range(size))
    yield PlainTuple()
    yield PlainTuple(("a", "b", "a", "c"))


def _probe(mod, kind, state, entries):
    source = kind(0)
    source.setstate(state)
    before = source.getstate()
    input_before = tuple(entries)
    reference = Random(0)
    reference.setstate(before)
    expected = list(entries)
    reference.shuffle(expected)
    expected_state = reference.getstate()
    try:
        arranged, continuation = mod.preview_shuffle(source, entries)
    except Exception:
        return True
    if source.getstate() != before or tuple(entries) != input_before:
        return True
    if list(arranged) != expected or continuation.getstate() != expected_state:
        return True

    if isinstance(arranged, list):
        arranged[:] = ["replacement"]
        arranged.append("extra")
        arranged.clear()
        if tuple(entries) != input_before:
            return True

    replacement = Random(491)
    replacement.gauss(0.0, 1.0)
    replacement_state = replacement.getstate()
    operations = (
        lambda rng: rng.random(),
        lambda rng: rng.getrandbits(0),
        lambda rng: rng.getrandbits(4097),
        lambda rng: rng.gauss(0.0, 1.0),
        lambda rng: rng.gauss(0.0, 1.0),
        lambda rng: rng.seed(2**300 + 9),
        lambda rng: rng.setstate(replacement_state),
    )
    for actor, observer in ((continuation, source), (source, continuation)):
        for operation in operations:
            observed = observer.getstate()
            operation(actor)
            if observer.getstate() != observed:
                return True
    return False


def attack(mod: ModuleType) -> bool:
    for kind in (Random, PlainRandom):
        for state in _states():
            for entries in _entries():
                if _probe(mod, kind, state, entries):
                    return True

    source = SystemRandom()
    source_before = source.__dict__.copy()
    for entries in ((), ("a",)):
        try:
            mod.preview_shuffle(source, entries)
        except Exception:
            if source.__dict__ != source_before:
                return True
        else:
            return True
    return False
