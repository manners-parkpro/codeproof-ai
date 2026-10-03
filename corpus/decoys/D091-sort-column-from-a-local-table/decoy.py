"""회원 목록 - 정렬 열은 같은 함수가 정해 둔 표에서 골라 넣는다."""

import sqlite3

_PAGE = 50


def list_members(conn: sqlite3.Connection, sort: str) -> list[tuple[int, str]]:
    columns = {"name": "name", "newest": "joined DESC", "oldest": "joined"}
    if sort not in columns:
        raise ValueError(f"정렬할 수 없는 열: {sort!r}")
    query = f"SELECT id, name FROM members ORDER BY {columns[sort]} LIMIT {_PAGE}"
    return conn.execute(query).fetchall()
