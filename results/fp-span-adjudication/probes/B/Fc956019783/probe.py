"""F3fcaa61719 / Fc956019783 (D069) - 시도를 다 쓴 실패 뒤에 notified=False 인 행이 원장에 남는가, 그 상태가 쌍의 문면과 맞서는가."""

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


def down(_delivery_id):
    raise ConnectionError("down")


def other(_delivery_id):
    raise RuntimeError("bug in notifier")


for notify in (down, other):
    mod._ledger.clear()
    try:
        mod.credit("d-1", 50, notify)
    except Exception as exc:  # noqa: BLE001
        print(f"notify={notify.__name__:5} -> {type(exc).__name__}: {exc} | ledger: {mod._ledger}")

# 호출자가 같은 배달로 다시 부르면 (증명이 재시도로 치는 경로) 같은 행에 덮어써 하나로 남는다
print("caller retries ->", mod.credit("d-1", 50, lambda _d: None), "| ledger:", mod._ledger)
