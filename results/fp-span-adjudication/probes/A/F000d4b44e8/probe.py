"""F000d4b44e8 (D066) - 음수 points 는 이체 방향을 뒤집는가, 잔액보다 큰 points 는 출금 쪽을 음수로 만드는가 (연결 모드 넷).

네트워크 · 외부 프로그램 없음. sqlite 는 메모리 안 (:memory:) 만 쓴다. 스키마는 쌍의 proof.py 와 같다.
"""

import importlib.util
import pathlib
import sqlite3
import sys

HERE = pathlib.Path(__file__).resolve().parent
MODES = ({}, {"isolation_level": None}, {"autocommit": True}, {"autocommit": False})


def load(name: str = "d066_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def wallet(mode: dict) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", **mode)
    conn.execute("CREATE TABLE wallet (user TEXT PRIMARY KEY, points INTEGER NOT NULL)")
    conn.execute("INSERT INTO wallet VALUES ('alice', 100), ('bob', 0)")
    conn.commit()
    return conn


mod = load()
for mode in MODES:
    results = {}
    for points in (-30, 500, 30):
        conn = wallet(mode)
        try:
            mod.transfer(conn, "alice", "bob", points)
            conn.commit()
            outcome = "ok"
        except Exception as exc:  # noqa: BLE001
            outcome = type(exc).__name__
        results[points] = (outcome, dict(conn.execute("SELECT user, points FROM wallet")))
        conn.close()
    print(mode or "{default}", results)
