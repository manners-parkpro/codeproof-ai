"""D069 - 시도를 다 써 실패를 올려도 적립 행이 원장에 남는가, 그리고 쌍이 그 행을 어떻게 다루는가.

네트워크 · 외부 프로그램 · 쓰기 없음 (proof.py 는 읽기만 한다).
"""

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROOF = pathlib.Path("<repo>/corpus/decoys/D069-retry-overwrites-the-same-key/proof.py")


def load(name: str = "d069_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()


def down(_delivery_id: str) -> None:
    raise ConnectionError("down")


def broken(_delivery_id: str) -> None:
    raise ValueError("boom")


try:
    mod.credit("d-1", 50, down)
except ConnectionError as exc:
    print("all attempts failed -> ConnectionError", exc)
print("ledger after failure:", mod._ledger)
try:
    mod.credit("d-2", 50, broken)
except ValueError:
    print("notify ValueError propagated | ledger:", mod._ledger)
print("caller retries d-1 ->", mod.credit("d-1", 50, lambda _d: None), "| ledger:", mod._ledger)
proof = PROOF.read_text(encoding="utf-8")
print("proof treats the caller's call after failure as a retry that must leave one row:", "호출자가 같은 배달로 다시 부른다" in proof)
