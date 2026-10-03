"""포인트 이체 - 감싼 세이브포인트가 실패한 이체를 되돌린다."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def _transaction(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("SAVEPOINT transfer")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK TO transfer")
        raise
    finally:
        conn.execute("RELEASE transfer")


def transfer(conn: sqlite3.Connection, src: str, dst: str, points: int) -> None:
    with _transaction(conn):
        taken = conn.execute("UPDATE wallet SET points = points - ? WHERE user = ?", (points, src))
        given = conn.execute("UPDATE wallet SET points = points + ? WHERE user = ?", (points, dst))
        if taken.rowcount != 1 or given.rowcount != 1:
            raise LookupError(f"{src} -> {dst}")
