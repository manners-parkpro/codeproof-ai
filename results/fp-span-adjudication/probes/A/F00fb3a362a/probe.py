"""D014 - 잔액보다 큰 금액을 transfer 로 보내면 출금 계좌가 음수가 되는가, 그리고 주장이 그것을 말하는가.

네트워크 · 외부 프로그램 · 쓰기 없음 (meta.toml 은 읽기만 한다).
"""

import importlib.util
import pathlib
import sys
import tomllib

HERE = pathlib.Path(__file__).resolve().parent
META = pathlib.Path("<repo>/corpus/decoys/D014-enclosing-transaction/meta.toml")


def load(name: str = "d014_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
ledger = mod.Ledger()
ledger.balances = {"a": 100, "b": 0}
mod.transfer(ledger, "a", "b", 150)
print("after transfer(a -> b, 150):", ledger.balances)
claim = tomllib.loads(META.read_text(encoding="utf-8"))["safety"]["claim"]
marker = "잔액보다 큰 금액은 받는다"
print("claim mentions overdraft:", marker in claim, "|", claim[claim.index(marker) - 1 :])
