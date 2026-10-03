"""D099 반증 - 와일드카드 · 이스케이프 후보 글자로 검색해 상관없는 상품이 나오는지 본다."""

from __future__ import annotations

import sqlite3
import string
from types import ModuleType

_PRODUCTS = ("100% cotton", "a_b socks", "a-b socks", "back\\slash", "plain tee", "cotton 50", "AB cap")
# 와일드카드 · 이스케이프 글자 · 그 조합 · 공백 정리와 엮인 것 (DESIGN §3.5 「입력 검사」)
_TERMS = ("%", "_", "\\", "a_b", "100%", "%cotton", "\\%", "\\_", "%%", "_ _", "  a_b  ", "a%b", "", "cotton")
# 🔴 이스케이프 문자로 쓰일 법한 글자 + 보통 글자 - 이스케이프 문자를 바꾸면서 그 글자 자신은 이스케이프하지
#    않는 약화가 이것으로만 드러난다 (독립 검토)
_ESCAPE_CANDIDATES = tuple(c + "a" for c in "!#$&*+-./:;=?@^|~")
# SQLite 는 텍스트 비교를 첫 NUL 에서 끊는다 - 거절해야 한다 (독립 검토)
_NUL = ("\x00", "tee\x00", "\x00%", "cotton\x00zzz")
_ASCII_FOLD = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE products (name TEXT)")
    conn.executemany("INSERT INTO products VALUES (?)", [(name,) for name in _PRODUCTS])
    return conn


def attack(mod: ModuleType) -> bool:
    """검색어가 글자 그대로 들어 있지 않은 상품이 결과에 나오거나, 들어 있는 상품이 빠지는가.

    정답은 공백 정리한 검색어가 이름에 ASCII 대소문자만 무시하고 들어 있는지로 낸다 - LIKE 를 쓰지 않는다
    (SQLite LIKE 는 ASCII 만 대소문자를 무시한다).

    decoy 는 % · _ · \\ 를 이스케이프해 글자로 찾고 NUL 이 든 검색어는 거절한다. twin 은 공백만 정리해
    와일드카드가 살아 있다.
    """
    conn = _db()
    for term in (*_TERMS, *_ESCAPE_CANDIDATES, *_NUL):
        try:
            got = mod.search(conn, term)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다, 돌려준 결과만 본다
            continue
        needle = " ".join(term.split()).translate(_ASCII_FOLD)
        if got != sorted(name for name in _PRODUCTS if needle in name.translate(_ASCII_FOLD)):
            return True
    # 평범한 검색은 그대로 된다 - 「전부 거절」은 안전이 아니다
    return mod.search(conn, "cotton") != ["100% cotton", "cotton 50"] or mod.search(conn, "a_b") != ["a_b socks"]
