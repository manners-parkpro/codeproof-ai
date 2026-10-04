"""배달 기록 - 큐는 같은 메시지를 다시 줄 수 있고, 그래도 _RECORD 가 message_id 마다 한 줄만 남긴다."""

import sqlite3
from contextlib import closing

_SCHEMA = "CREATE TABLE IF NOT EXISTS deliveries (message_id TEXT NOT NULL, body TEXT NOT NULL)"
_INDEX = "CREATE INDEX IF NOT EXISTS deliveries_message_id ON deliveries (message_id)"
_RECORD = (
    "INSERT INTO deliveries (message_id, body)"
    " VALUES (:id, :body)"
)


def record(path: str, message_id: str, body: str) -> None:
    with closing(sqlite3.connect(path)) as conn:
        if conn.execute("PRAGMA encoding").fetchone()[0] != "UTF-8":
            raise ValueError("UTF-8 이 아닌 데이터베이스 파일에는 쓰지 않는다")
        with conn:
            conn.execute(_SCHEMA)
            conn.execute(_INDEX)
            conn.execute(_RECORD, {"id": message_id, "body": body})
