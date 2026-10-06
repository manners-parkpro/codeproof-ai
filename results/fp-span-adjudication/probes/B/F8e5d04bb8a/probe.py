"""F8e5d04bb8a (D028) - make_cursor: object 와 type: ignore 가 실행 중의 잘못된 동작을 만드는가.

지적은 정적 타입 검사가 호출 가능 여부 · 반환 타입을 못 본다는 것이다. 실행에서는 store 가 커서를
만들고 어느 경로로든 닫는지를 본다 (주장). 타입 주석은 실행에 영향이 없다.
"""

import importlib.util
import inspect
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F8e5d04bb8a", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Cursor:
    def __init__(self):
        self.closed = False
        self.rows = []

    def execute(self, sql, params):
        self.rows.append(params[0])

    def close(self):
        self.closed = True


mod = _load()
print("store signature:", inspect.signature(mod.store))
made = []


def make():
    made.append(Cursor())
    return made[-1]


print("store ->", mod.store(make, ["a", "b"]), "| closed:", made[-1].closed, "| rows:", made[-1].rows)


def rows_then_fail():
    yield "a"
    raise RuntimeError("source failed")


try:
    mod.store(make, rows_then_fail())
except RuntimeError:
    pass
print("exception path closed:", made[-1].closed)
