"""F00fb3a362a / Faf2d72cd4b (D014) - 잔액보다 큰 금액의 이체가 출금 계좌를 음수로 만드는가."""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = HERE.name


def _load():
    spec = importlib.util.spec_from_file_location(f"decoy_{TAG}", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
ledger = mod.Ledger()
ledger.balances = {"a": 100, "b": 0}
mod.transfer(ledger, "a", "b", 250)
print("transfer 250 from a=100 ->", ledger.balances, "| no exception, sum kept:", sum(ledger.balances.values()) == 100)

# 0 이하 금액은 거절된다 (선례 「음수」는 이미 고쳤다)
for amount in (0, -1):
    book = mod.Ledger()
    book.balances = {"a": 100, "b": 0}
    try:
        mod.transfer(book, "a", "b", amount)
    except ValueError as exc:
        print("amount", amount, "->", type(exc).__name__, exc, "| balances", book.balances)
print("python", sys.version.split()[0])
