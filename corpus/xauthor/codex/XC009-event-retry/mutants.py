WEAKENED = {
    "same-key retry loses uniqueness": [
        ("event_id BLOB NOT NULL PRIMARY KEY,", "event_id BLOB NOT NULL,"),
    ],
    "different payload becomes a second event": [
        ("event_id BLOB NOT NULL PRIMARY KEY,\n    payload BLOB NOT NULL", "event_id BLOB NOT NULL,\n    payload BLOB NOT NULL,\n    PRIMARY KEY(event_id, payload)"),
    ],
    "different keys with equal payload collapse": [
        ("payload BLOB NOT NULL", "payload BLOB NOT NULL UNIQUE"),
    ],
    "retry overwrites first payload": [
        ("INSERT INTO events(event_id, payload) VALUES (?, ?) ON CONFLICT DO NOTHING", "INSERT OR REPLACE INTO events(event_id, payload) VALUES (?, ?)"),
    ],
    "long identifiers collapse": [
        ("key = event_id.encode(\"utf-8\", \"surrogatepass\")", "key = event_id[:64].encode(\"utf-8\", \"surrogatepass\")"),
    ],
    "case distinct identifiers collapse": [
        ("key = event_id.encode(\"utf-8\", \"surrogatepass\")", "key = event_id.lower().encode(\"utf-8\", \"surrogatepass\")"),
    ],
    "NUL suffix is discarded": [
        ("key = event_id.encode(\"utf-8\", \"surrogatepass\")", "key = event_id.split(\"\\x00\", 1)[0].encode(\"utf-8\", \"surrogatepass\")"),
    ],
    "lone surrogates lose identity": [
        ("key = event_id.encode(\"utf-8\", \"surrogatepass\")", "key = event_id.encode(\"utf-8\", \"replace\")"),
    ],
    "str Enum representation changes identity": [
        ("key = event_id.encode(\"utf-8\", \"surrogatepass\")", "key = str(event_id).encode(\"utf-8\", \"surrogatepass\")"),
    ],
    "large payload is truncated": [
        ("body = payload.encode(\"utf-8\", \"surrogatepass\")", "body = payload[:64].encode(\"utf-8\", \"surrogatepass\")"),
    ],
    "ack failure rolls back first insertion": [
        ("            )\n        acknowledge()", "            )\n            acknowledge()"),
    ],
    "prior records erased before a new delivery": [
        ("    for attempt in range(attempts):", "    journal._db.execute(\"DELETE FROM events\")\n    for attempt in range(attempts):"),
    ],
    "retries invent a fresh identifier": [
        ("journal.record(event_id, payload, acknowledge)", "journal.record(event_id if attempt == 0 else event_id + str(attempt), payload, acknowledge)"),
    ],
    "nonpositive attempt performs a write": [
        ("        raise ValueError(\"attempts must be positive\")", "        journal.record(event_id, payload, acknowledge)\n        return"),
    ],
}

SAFE = {
    "unique constraint instead of primary key": [
        ("event_id BLOB NOT NULL PRIMARY KEY,", "event_id BLOB NOT NULL UNIQUE,"),
    ],
    "equivalent SQLite ignore syntax": [
        ("INSERT INTO events(event_id, payload) VALUES (?, ?) ON CONFLICT DO NOTHING", "INSERT OR IGNORE INTO events(event_id, payload) VALUES (?, ?)"),
    ],
    "explicit conflict target": [
        ("ON CONFLICT DO NOTHING", "ON CONFLICT(event_id) DO NOTHING"),
    ],
    "different invalid attempts exception": [
        ("raise ValueError(\"attempts must be positive\")", "raise RuntimeError(\"attempts must be positive\")"),
    ],
    "snapshot order changed": [
        ("SELECT event_id, payload FROM events", "SELECT event_id, payload FROM events ORDER BY event_id DESC"),
    ],
    "integer subclass range normalization": [
        ("range(attempts)", "range(int(attempts))"),
    ],
    "different lossless serialization": [
        ("\"\"\"이벤트 수신 재시도 - 커밋된 식별자의 기본 키 제약으로 중복 기록을 막는다.\"\"\"\n\nimport sqlite3\nfrom collections.abc import Callable\n\n\n_SCHEMA = \"\"\"\nCREATE TABLE events (\n    event_id BLOB NOT NULL PRIMARY KEY,\n    payload BLOB NOT NULL\n)\n\"\"\"\n\n\nclass EventJournal:\n    def __init__(self) -> None:\n        self._db = sqlite3.connect(\":memory:\")\n        self._db.execute(_SCHEMA)\n\n    def record(self, event_id: str, payload: str, acknowledge: Callable[[], None]) -> None:\n        key = event_id.encode(\"utf-8\", \"surrogatepass\")\n        body = payload.encode(\"utf-8\", \"surrogatepass\")\n        with self._db:\n            self._db.execute(\n                \"INSERT INTO events(event_id, payload) VALUES (?, ?) ON CONFLICT DO NOTHING\",\n                (key, body),\n            )\n        acknowledge()\n\n    def entries(self) -> list[tuple[str, str]]:\n        return [\n            (key.decode(\"utf-8\", \"surrogatepass\"), body.decode(\"utf-8\", \"surrogatepass\"))\n            for key, body in self._db.execute(\"SELECT event_id, payload FROM events\")\n        ]\n\n    def close(self) -> None:\n        self._db.close()\n\n\ndef deliver(\n    journal: EventJournal,\n    event_id: str,\n    payload: str,\n    acknowledge: Callable[[], None],\n    attempts: int = 3,\n) -> None:\n    if attempts < 1:\n        raise ValueError(\"attempts must be positive\")\n    for attempt in range(attempts):\n        try:\n            journal.record(event_id, payload, acknowledge)\n            return\n        except TimeoutError:\n            if attempt == attempts - 1:\n                raise\n", "\"\"\"이벤트 수신 재시도 - 커밋된 식별자의 기본 키 제약으로 중복 기록을 막는다.\"\"\"\n\nimport sqlite3\nfrom collections.abc import Callable\n\n\n_SCHEMA = \"\"\"\nCREATE TABLE events (\n    event_id BLOB NOT NULL PRIMARY KEY,\n    payload BLOB NOT NULL\n)\n\"\"\"\n\n\nclass EventJournal:\n    def __init__(self) -> None:\n        self._db = sqlite3.connect(\":memory:\")\n        self._db.execute(_SCHEMA)\n\n    def record(self, event_id: str, payload: str, acknowledge: Callable[[], None]) -> None:\n        key = event_id.encode(\"utf-32-le\", \"surrogatepass\")\n        body = payload.encode(\"utf-32-le\", \"surrogatepass\")\n        with self._db:\n            self._db.execute(\n                \"INSERT INTO events(event_id, payload) VALUES (?, ?) ON CONFLICT DO NOTHING\",\n                (key, body),\n            )\n        acknowledge()\n\n    def entries(self) -> list[tuple[str, str]]:\n        return [\n            (key.decode(\"utf-32-le\", \"surrogatepass\"), body.decode(\"utf-32-le\", \"surrogatepass\"))\n            for key, body in self._db.execute(\"SELECT event_id, payload FROM events\")\n        ]\n\n    def close(self) -> None:\n        self._db.close()\n\n\ndef deliver(\n    journal: EventJournal,\n    event_id: str,\n    payload: str,\n    acknowledge: Callable[[], None],\n    attempts: int = 3,\n) -> None:\n    if attempts < 1:\n        raise ValueError(\"attempts must be positive\")\n    for attempt in range(attempts):\n        try:\n            journal.record(event_id, payload, acknowledge)\n            return\n        except TimeoutError:\n            if attempt == attempts - 1:\n                raise\n"),
    ],
}

RACY = {
}

