"""D051 - run 이 부를 때마다 _totals 를 비우지 않고 누적한 값을 돌려주는가, 그리고 쌍이 그것을 어떻게 다루는가.

네트워크 · 외부 프로그램 · 쓰기 없음 (proof.py 는 읽기만 한다).
"""

import importlib.util
import pathlib
import sys
import threading

HERE = pathlib.Path(__file__).resolve().parent
PROOF = pathlib.Path("<repo>/corpus/decoys/D051-single-writer-by-construction/proof.py")


def load(name: str = "d051_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
print("run([1,2,3]) ->", mod.run([1, 2, 3]))
print("run([1,2,3]) again ->", mod.run([1, 2, 3]), "| _totals:", mod._totals)

# 여러 호출자가 나눠 부르면 _totals 가 전부의 합이 된다 - 증명이 기대하는 모양
mod._totals["sum"] = 0
parts = [list(range(k, 400, 4)) for k in range(4)]
callers = [threading.Thread(target=mod.run, args=(part,)) for part in parts]
for c in callers:
    c.start()
for c in callers:
    c.join()
print("4 concurrent callers -> _totals:", mod._totals["sum"], "== sum(range(400)):", mod._totals["sum"] == sum(range(400)))
proof = PROOF.read_text(encoding="utf-8")
print("proof resets the running total before each scenario:", proof.count('mod._totals["sum"] = 0'))
print("proof expects the total of all callers:", 'if mod._totals["sum"] != sum(range(size)):' in proof)
