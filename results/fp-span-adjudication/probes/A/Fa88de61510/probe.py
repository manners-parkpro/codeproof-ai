"""Fa88de61510 (D056) - work 가 동기로 낸 BaseException 에서 스팬이 기록되지 않는가, 그리고 예외가 감춰지는가.

네트워크 · 외부 프로그램 · 쓰기 없음.
"""

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d056_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class Halt(BaseException):
    """Exception 이 아닌 사용자 정의 동기 예외."""


def exits():
    sys.exit(3)


def interrupted():
    raise KeyboardInterrupt  # 동기로 올린 것 - 신호가 아니다


def halts():
    raise Halt


def fails():
    raise ValueError("downstream failed")


def ok():
    return 7


mod = load()
for work in (exits, interrupted, halts, fails, ok):
    start = len(mod._spans)
    try:
        result = mod.measured(work.__name__, work)
        outcome = f"returned {result!r}"
    except BaseException as exc:  # noqa: BLE001
        outcome = f"propagated {type(exc).__name__} (same object type as raised)"
    print(f"{work.__name__}: {outcome} | spans added: {mod._spans[start:]}")
