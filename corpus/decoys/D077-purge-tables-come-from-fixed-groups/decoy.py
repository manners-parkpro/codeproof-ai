"""보관 기간이 지난 행 정리 - 테이블 이름은 정해 둔 묶음에서만 고른다."""

import sqlite3

_GROUPS = {
    "security": ("audit_log", "login_events"),
    "batch": ("job_runs",),
}


def _purge(conn: sqlite3.Connection, table: str, cutoff: str) -> int:
    cursor = conn.execute(f"DELETE FROM {table} WHERE created_at < ?", (cutoff,))
    cursor.fetchall()
    return cursor.rowcount


def purge_expired(conn: sqlite3.Connection, group: str, cutoff: str) -> int:
    if group not in _GROUPS:
        raise ValueError(f"모르는 묶음: {group}")
    tables = _GROUPS[group]
    return sum(_purge(conn, table, cutoff) for table in tables)
