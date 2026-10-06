"""F0285e1b086 / Fdba13194b1 (D051) - run 이 호출마다 초기화하지 않고 누적한 합을 돌려주는가, 그것이 쌍의 문면과 맞서는가."""

import importlib.util
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = HERE.name


def _load():
    spec = importlib.util.spec_from_file_location(f"decoy_{TAG}", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
print("run([1,2]) ->", mod.run([1, 2]))
print("run([1,2]) again ->", mod.run([1, 2]), "| _totals:", mod._totals)

# 여러 호출자가 run 을 함께 부를 때 전체 합 - 누적이어야 「호출끼리 겹쳐도 합이 맞다」를 잴 수 있다
mod._totals["sum"] = 0
parts = [list(range(k, 400, 4)) for k in range(4)]
callers = [threading.Thread(target=mod.run, args=(p,)) for p in parts]
for c in callers:
    c.start()
for c in callers:
    c.join()
print("4 concurrent callers -> _totals:", mod._totals["sum"], "| sum(range(400)):", sum(range(400)))
