"""마이그레이션 - DDL 이 모듈 상수다."""

from typing import Protocol

_DDL = "ALTER TABLE audit ADD COLUMN trace_id TEXT"


class Cursor(Protocol):
    def execute(self, sql: str) -> object: ...


def migrate(cursor: Cursor) -> None:
    cursor.execute(_DDL)
