"""F24e53d5f6c / Fc0ab38f85e (D144) - 범위 안 float 좌표를 받아 정수가 아닌 번호를 내는가, 선언 타입 int 안에서는 어떤가."""

import enum
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = HERE.name


def _load():
    spec = importlib.util.spec_from_file_location(f"decoy_{TAG}", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()

# 선언 타입 밖 - float
for row, col in ((1.5, 2.0), (1.0, 2.0)):
    cell = mod.Cell(row, col)
    print(f"Cell({row}, {col}) accepted -> index {mod.index(cell)!r} ({type(mod.index(cell)).__name__}) | isinstance(row, int): {isinstance(row, int)}")


# 선언 타입 안 - int · int 하위 클래스 · IntEnum 은 언제나 정수 번호 · bool 은 거절
class Small(int):
    pass


class Pos(enum.IntEnum):
    ONE = 1
    EIGHT = 8


bad = []
for row in range(6):
    for col in range(9):
        for r, c in ((row, col), (Small(row), Small(col))):
            n = mod.index(mod.Cell(r, c))
            if type(n) is not int or not 0 <= n < 54:
                bad.append((r, c, n))
print("in-type cells with non-int or out-of-range index:", bad, "| IntEnum:", mod.index(mod.Cell(Pos.ONE, Pos.EIGHT)))
try:
    mod.Cell(True, 3)
except TypeError as exc:
    print("bool ->", type(exc).__name__)
