"""F000d4b44e8 (D066) - 음수 points 가 이체 방향을 뒤집는가 · 잔액보다 큰 points 가 출금 지갑을 음수로 만드는가.

메모리 안의 sqlite 만 쓴다. 연결 모드 넷 모두에서 본다 (증명과 같은 모드).
"""

import importlib.util
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F000d4b44e8", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
MODES = ({}, {"isolation_level": None}, {"autocommit": True}, {"autocommit": False})


def wallet(mode):
    conn = sqlite3.connect(":memory:", **mode)
    conn.execute("CREATE TABLE wallet (user TEXT PRIMARY KEY, points INTEGER NOT NULL)")
    conn.execute("INSERT INTO wallet VALUES ('alice', 100), ('bob', 0)")
    conn.commit()
    return conn


def balances(conn):
    return dict(conn.execute("SELECT user, points FROM wallet ORDER BY user").fetchall())


for mode in MODES:
    for points in (-30, 250):
        conn = wallet(mode)
        try:
            mod.transfer(conn, "alice", "bob", points)  # alice -> bob 로 부른다
            conn.commit()
            outcome = "ok"
        except Exception as exc:  # noqa: BLE001
            outcome = f"{type(exc).__name__}: {exc}"
        print(f"mode={mode!s:28} transfer(alice -> bob, {points:>4}) -> {outcome:4} | balances {balances(conn)}")
        conn.close()
