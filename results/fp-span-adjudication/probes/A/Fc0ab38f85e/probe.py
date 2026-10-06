"""D144 - 판 안의 float 좌표를 받는가, 그리고 선언 타입 int 안의 값(평범한 하위 타입 포함)에서는 index 가 정수인가.

네트워크 · 외부 프로그램 · 쓰기 없음.
"""

import enum
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d144_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
cell = mod.Cell(1.5, 2.0)
print("Cell(1.5, 2.0) accepted:", cell, "| index:", mod.index(cell), type(mod.index(cell)).__name__, "| isinstance(1.5, int):", isinstance(1.5, int))


class Sub(int):
    pass


class Pos(enum.IntEnum):
    ONE = 1
    EIGHT = 8


bad = []
seen = {}
for row in range(mod.ROWS):
    for col in range(mod.COLS):
        for r, c in ((row, col), (Sub(row), Sub(col))):
            n = mod.index(mod.Cell(r, c))
            if type(n) is not int or not 0 <= n < 54 or seen.setdefault(n, (row, col)) != (row, col):
                bad.append((row, col, n))
print("int and int-subclass cells: bad indexes:", bad, "| distinct:", len(seen))
print("IntEnum cell index type:", type(mod.index(mod.Cell(Pos.ONE, Pos.EIGHT))).__name__)
for coords in ((True, 1), (1, False), (6, 0), (0, 9), (-1, 0)):
    try:
        mod.Cell(*coords)
        print("accepted (unexpected):", coords)
    except (TypeError, ValueError) as exc:
        print("rejected:", coords, type(exc).__name__)
