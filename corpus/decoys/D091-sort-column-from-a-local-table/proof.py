"""D091 반증 - 표에 없는 정렬 값을 넣고 실제로 실행된 문장을 본다."""

from __future__ import annotations

import re
import sqlite3
from types import ModuleType

_ALLOWED = {"name", "joined DESC", "joined"}
_ORDER = re.compile(r"ORDER BY (.*) LIMIT 50$", re.DOTALL)
# 올바른 키의 닮은꼴 · 꼬리 · 구분자 · 하위 질의 (DESIGN §3.5 「입력 검사」)
_PROBES = (
    "name ",
    " name",
    "NAME",
    "name DESC",
    "name;",
    "name -- x",
    "newest\n",
    "joined DESC, (SELECT count(*) FROM sqlite_master)",
    "(SELECT count(*) FROM sqlite_master)",
    "id",
    "",
    # 맞는 키 뒤에 쉼표 · 콜론으로 다른 절을 잇는 꼴 - 첫 칸만 확인하는 약화를 잡는다 (독립 검토)
    "name,(SELECT count(*) FROM sqlite_master)",
    "name:desc",
    "name:, (SELECT count(*) FROM sqlite_master)",
)


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE members (id INTEGER, name TEXT, joined TEXT)")
    conn.executemany(
        "INSERT INTO members VALUES (?, ?, ?)",
        [(1, "kim", "2024-03-01"), (2, "lee", "2023-01-15"), (3, "park", "2025-07-30")],
    )
    return conn


def attack(mod: ModuleType) -> bool:
    """표에 없는 문자열이 실행된 문장의 ORDER BY 자리에 닿는가.

    실제로 실행된 문장을 sqlite 의 추적 콜백으로 모아 본다 - 결과 행만 보면 정렬을 바꾸지 않는 주입이
    빠진다.

    decoy 는 키가 아닌 sort 를 ValueError 로 거절하고, 키는 표의 상수 값으로만 바꿔 넣는다.
    twin 은 표에 없는 sort 를 그대로 넣는다.
    """
    conn = _db()
    executed: list[str] = []
    conn.set_trace_callback(executed.append)
    for sort in _PROBES:
        try:
            mod.list_members(conn, sort)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다, 실행된 문장만 본다
            pass
    for statement in executed:
        order = _ORDER.search(statement)
        if order is None or order.group(1) not in _ALLOWED:
            return True

    # 정해 둔 키는 그대로 정렬한다 - 「전부 거절」은 안전이 아니다
    names = [name for _, name in mod.list_members(conn, "name")]
    newest = [name for _, name in mod.list_members(conn, "newest")]
    return names != ["kim", "lee", "park"] or newest != ["park", "kim", "lee"]
