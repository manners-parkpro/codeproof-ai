"""상품 검색 - 이웃한 두 함수 중 하나만 LIKE 와일드카드를 막는다."""

import sqlite3


def _tidy(term: str) -> str:
    """표시용 공백 정리. 와일드카드는 건드리지 않는다."""
    return " ".join(term.split())


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search(conn: sqlite3.Connection, term: str) -> list[str]:
    if any(ch in term for ch in "\x00\ufffd\ufffe\uffff"):
        raise ValueError("검색어에 NUL 이나 SQLite 가 U+FFFD 로 읽는 글자가 들어 있다")
    pattern = f"%{_escape_like(_tidy(term))}%"
    rows = conn.execute(
        "SELECT name FROM products WHERE name LIKE ? ESCAPE '\\' ORDER BY name LIMIT 100", (pattern,)
    )
    return [name for (name,) in rows]
