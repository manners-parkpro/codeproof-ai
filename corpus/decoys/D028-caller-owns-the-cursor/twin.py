"""배치 삽입 - 커서 소유권이 바깥에 있다."""

from collections.abc import Iterable
from typing import Protocol


class Cursor(Protocol):
    def execute(self, sql: str, params: tuple[str, ...]) -> object: ...
    def close(self) -> None: ...


def _insert_all(cursor: Cursor, rows: Iterable[str]) -> int:
    count = 0
    for row in rows:
        cursor.execute("INSERT INTO audit(line) VALUES (?)", (row,))
        count += 1
    return count


def store(make_cursor: object, rows: Iterable[str]) -> int:
    cursor = make_cursor()  # type: ignore[operator]
    return _insert_all(cursor, rows)
