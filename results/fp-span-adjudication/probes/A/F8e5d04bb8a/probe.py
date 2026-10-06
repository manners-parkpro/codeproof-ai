"""F8e5d04bb8a (D028) - make_cursor 의 주석이 object 인 것이 실행 결함을 만드는가.

네트워크 · 외부 프로그램 · 쓰기 없음. 타입 검사기는 돌리지 않는다 (외부 프로그램) - 주석을 읽어 보인다.
"""

import importlib.util
import pathlib
import sys
import typing

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d028_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
print("store annotations:", typing.get_type_hints(mod.store))
source = (HERE / "decoy.py").read_text(encoding="utf-8")
print("type: ignore on the call line:", "# type: ignore[operator]" in source)


class Cur:
    def __init__(self) -> None:
        self.closed = False
        self.rows: list[str] = []

    def execute(self, sql: str, params: tuple[str, ...]) -> object:
        self.rows.append(params[0])
        return None

    def close(self) -> None:
        self.closed = True


cursor = Cur()
print("normal path:", mod.store(lambda: cursor, ["a", "b"]), "closed:", cursor.closed)


def exploding():
    yield "ok"
    raise RuntimeError("row source failed")


cursor2 = Cur()
try:
    mod.store(lambda: cursor2, exploding())
except RuntimeError:
    print("exception path closed:", cursor2.closed)

# 주석 object 가 받는 값 중 호출할 수 없는 것 - 커서가 없으니 닫을 것도 없다
try:
    mod.store(42, ["a"])
except TypeError as exc:
    print("store(42, ...):", type(exc).__name__, exc)
