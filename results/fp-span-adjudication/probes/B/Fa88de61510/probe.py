"""Fa88de61510 (D056) - 동기 BaseException 에서 스팬이 기록되지 않는가, 그 예외는 감춰지는가."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_Fa88de61510", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


class Halt(BaseException):
    pass


def raiser(exc):
    def work():
        raise exc
    return work


for exc in (ValueError("v"), SystemExit(3), KeyboardInterrupt(), GeneratorExit(), Halt()):
    mod._spans.clear()
    try:
        mod.measured("call", raiser(exc))
    except BaseException as got:  # noqa: BLE001
        print(f"{type(exc).__name__:17} -> propagated same object: {got is exc} | spans: {mod._spans}")


# 생성기 안의 with 블록을 일찍 닫는 경우 (GeneratorExit 이 블록 안에서 난다)
def gen():
    with mod.span("gen"):
        yield 1
        yield 2


mod._spans.clear()
g = gen()
next(g)
g.close()
print("generator closed early -> spans:", mod._spans)
print("success -> ", mod.measured("ok", lambda: 7), mod._spans)
