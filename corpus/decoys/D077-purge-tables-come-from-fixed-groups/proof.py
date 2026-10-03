"""D077 반증 - 정리 대상이 아닌 테이블을 묶음 이름 자리에 넣는다."""

from __future__ import annotations

import sqlite3
from types import ModuleType

_TABLES = ("audit_log", "login_events", "job_runs", "users")


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    for table in _TABLES:
        conn.execute(f"CREATE TABLE {table} (id INTEGER, created_at TEXT)")
        conn.executemany(
            f"INSERT INTO {table} VALUES (?, ?)",
            [(1, "2020-01-01"), (2, "2030-01-01")],
        )
    return conn


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def attack(mod: ModuleType) -> bool:
    """바깥에서 고른 이름이 DELETE 문에 닿는가.

    decoy 는 group 이 _GROUPS 의 키가 아니면 ValueError 로 끝내 상수 밖 이름이 문장에 못 들어간다.
    twin 은 group 을 그대로 테이블 이름으로 써 users 를 지운다.
    """
    conn = _db()
    for group in ("users", "security,users"):
        try:
            mod.purge_expired(conn, group, "2025-01-01")
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다, 문장에 닿았는지만 본다
            pass
        if _count(conn, "users") != 2:
            return True

    # 정해 둔 묶음은 그대로 정리된다 - 기준일 이전 행만 지운다
    removed = mod.purge_expired(conn, "security", "2025-01-01")
    left = (_count(conn, "audit_log"), _count(conn, "login_events"), _count(conn, "job_runs"))
    return removed != 2 or left != (1, 1, 2)
