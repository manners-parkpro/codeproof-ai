"""F3e10c1de6a (D060) - NaN 은 1 / 0 에 닿는가, 그리고 선언 타입 int 안의 값은 닿는가.

네트워크 · 외부 프로그램 · 쓰기 없음.
"""

import enum
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d060_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
nan = float("nan")
try:
    mod.discount(nan)
except ZeroDivisionError:
    print("discount(nan) -> ZeroDivisionError | isinstance(nan, int):", isinstance(nan, int))


class Amount(int):
    pass


class Tier(enum.IntEnum):
    LOW = 99
    MID = 100


reached = []
samples = [*range(-20000, 20001), -(2**80), 2**80, -(10**400), 10**400, True, False, Amount(-5), Amount(99), Amount(100), Tier.LOW, Tier.MID]
for amount in samples:
    try:
        mod.discount(amount)
    except ZeroDivisionError:
        reached.append(amount)
print(f"int-typed samples: {len(samples)} | reaching 1/0: {reached}")
