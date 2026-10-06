"""F3e10c1de6a (D060) - 1 / 0 에 닿는 값이 선언 타입 int 안에 있는가 (NaN 은 int 가 아니다)."""

import enum
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F3e10c1de6a", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


class Amount(int):
    pass


class Level(enum.IntEnum):
    LOW = 99
    HIGH = 1000


reached = []
values = [*range(-2000, 2001), 2**200, -(2**200), True, False, Amount(150), Amount(-7), Level.LOW, Level.HIGH]
for amount in values:
    try:
        mod.discount(amount)
    except ZeroDivisionError:
        reached.append(amount)
print("int values tried:", len(values), "| reached 1/0:", reached)

nan = float("nan")
print("isinstance(nan, int):", isinstance(nan, int))
try:
    mod.discount(nan)
except ZeroDivisionError as exc:
    print("discount(nan) ->", type(exc).__name__, exc)
