"""라우팅 표 변조 시도 - 원본과 노출 객체의 변경 뒤 의미를 확인한다."""

from enum import IntEnum
from operator import delitem, iadd, imul, setitem
from types import ModuleType


class OrdinaryInt(int):
    pass


class Boundary(IntEnum):
    NEGATIVE = -1
    LOW = 0
    BEFORE_MIDDLE = 49
    MIDDLE = 50
    BEFORE_HIGH = 79
    HIGH = 80


EXPECTED = ((0, 3), (50, 2), (80, 1))
LOADS = (
    *range(-2, 83),
    -(2**4096),
    2**4096,
    False,
    True,
    *Boundary,
    *(OrdinaryInt(n) for n in (-2**256, 0, 49, 50, 79, 80, 2**256)),
)


def broken(mod):
    try:
        rows = tuple(tuple(row) for row in mod.routing_table())
        if rows != EXPECTED:
            return True
        for load in LOADS:
            expected = 3 if load < 50 else 2 if load < 80 else 1
            if mod.route(load) != expected:
                return True
    except Exception:
        return True
    return False


def variants(seq):
    result = [seq, seq[:], seq[::-1], seq[1:], seq[:0]]
    for operation in (
        lambda: seq + seq,
        lambda: seq * 2,
        lambda: seq * 0,
        lambda: seq.copy(),
    ):
        try:
            result.append(operation())
        except Exception:
            pass
    return result


def operations(seq, row):
    value = OrdinaryInt(99) if row else [OrdinaryInt(99), Boundary.HIGH]
    second = False if row else [False, OrdinaryInt(99)]
    batch = [value, second]
    return (
        lambda: setitem(seq, 0, value),
        lambda: setitem(seq, -1, value),
        lambda: setitem(seq, 1, value),
        lambda: setitem(seq, 0, 2**1024 if row else [2**1024, 1]),
        lambda: setitem(seq, 0, False if row else [False, 1]),
        lambda: setitem(seq, slice(None), batch),
        lambda: setitem(seq, slice(0, 0), batch),
        lambda: setitem(seq, slice(None, None, 2), [value] * len(list(seq)[::2])),
        lambda: delitem(seq, 0),
        lambda: delitem(seq, -1),
        lambda: delitem(seq, slice(None)),
        lambda: seq.append(value),
        lambda: seq.extend(batch),
        lambda: seq.insert(0, value),
        lambda: seq.pop(),
        lambda: seq.remove(seq[0]),
        lambda: seq.clear(),
        lambda: seq.reverse(),
        lambda: seq.sort(reverse=True),
        lambda: iadd(seq, batch),
        lambda: iadd(seq, tuple(batch)),
        lambda: imul(seq, 0),
        lambda: imul(seq, 2),
        lambda: imul(seq, -1),
    )


def attack(mod: ModuleType) -> bool:
    if broken(mod):
        return True
    tables = [mod.BOOTSTRAP, mod.ROUTES, mod.routing_table()]
    targets = []
    for table in tables:
        for view in variants(table):
            targets.append((view, False))
            for row in view:
                targets.extend((part, True) for part in variants(row))
    for seq, row in targets:
        for operation in operations(seq, row):
            try:
                operation()
            except Exception:
                pass
            if broken(mod):
                return True
    return broken(mod)
