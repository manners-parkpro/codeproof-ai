"""이벤트 수신 재시도 - 커밋된 식별자의 기본 키 제약으로 중복 기록을 막는다."""

import sqlite3
from collections.abc import Callable


_SCHEMA = """
CREATE TABLE events (
    event_id BLOB NOT NULL,
    payload BLOB NOT NULL
)
"""


class EventJournal:
    def __init__(self) -> None:
        self._db = sqlite3.connect(":memory:")
        self._db.execute(_SCHEMA)

    def record(self, event_id: str, payload: str, acknowledge: Callable[[], None]) -> None:
        key = event_id.encode("utf-8", "surrogatepass")
        body = payload.encode("utf-8", "surrogatepass")
        with self._db:
            self._db.execute(
                "INSERT INTO events(event_id, payload) VALUES (?, ?) ON CONFLICT DO NOTHING",
                (key, body),
            )
        acknowledge()

    def entries(self) -> list[tuple[str, str]]:
        return [
            (key.decode("utf-8", "surrogatepass"), body.decode("utf-8", "surrogatepass"))
            for key, body in self._db.execute("SELECT event_id, payload FROM events")
        ]

    def close(self) -> None:
        self._db.close()


def deliver(
    journal: EventJournal,
    event_id: str,
    payload: str,
    acknowledge: Callable[[], None],
    attempts: int = 3,
) -> None:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        try:
            journal.record(event_id, payload, acknowledge)
            return
        except TimeoutError:
            if attempt == attempts - 1:
                raise
