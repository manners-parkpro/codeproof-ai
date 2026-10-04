"""D066 반증 - 지갑이 없는 이체로 부분 갱신을 노린다 (연결 모드 넷 모두)."""

from __future__ import annotations

import sqlite3
from types import ModuleType
from typing import Any

# 🔴 연결 모드는 호출자가 정하고 모드마다 트랜잭션이 열리는 방식이 다르다. 기본 모드 하나만 치면
#    autocommit 연결에서 rollback 이 무력한 가드도 통과한다 - 독립 검토가 그렇게 찾았다.
_MODES: tuple[dict[str, Any], ...] = (
    {},  # 기존 방식 - DML 앞에서 암묵적으로 연다
    {"isolation_level": None},  # autocommit
    {"autocommit": True},
    {"autocommit": False},  # PEP 249 - 트랜잭션이 늘 열려 있다
)


class _Interrupting:
    """두 번째 UPDATE 에서 KeyboardInterrupt 를 던지는 연결 대리자 - Exception 밖의 실패."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._updates = 0

    def execute(self, sql: str, *args: Any) -> sqlite3.Cursor:  # noqa: ANN401
        if sql.lstrip().upper().startswith("UPDATE"):
            self._updates += 1
            if self._updates == 2:
                raise KeyboardInterrupt
        return self._conn.execute(sql, *args)


def _wallet(mode: dict[str, Any]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", **mode)
    conn.execute("CREATE TABLE wallet (user TEXT PRIMARY KEY, points INTEGER NOT NULL)")
    conn.execute("INSERT INTO wallet VALUES ('alice', 100), ('bob', 0)")
    conn.commit()
    return conn


def _balances(conn: sqlite3.Connection) -> tuple[int, int]:
    rows = dict(conn.execute("SELECT user, points FROM wallet").fetchall())
    return int(rows["alice"]), int(rows["bob"])


def _broken(mod: ModuleType, mode: dict[str, Any]) -> bool:
    conn = _wallet(mode)
    try:
        conn.execute("UPDATE wallet SET points = 7 WHERE user = 'bob'")  # 호출자가 먼저 한 일
        for src, dst in (("alice", "nobody"), ("nobody", "alice")):
            try:
                mod.transfer(conn, src, dst, 30)
            except LookupError:
                pass  # 없는 지갑이라는 거절은 정상이다 - 흔적이 남았는지가 관건이다
            else:
                return True  # 없는 지갑으로 이체가 성공했다
        try:
            mod.transfer(_Interrupting(conn), "alice", "bob", 30)
        except KeyboardInterrupt:
            pass  # 두 UPDATE 사이의 중단 - 차감만 남으면 안 된다
        conn.commit()  # 남은 흔적이 있으면 여기서 확정된다
        if _balances(conn) != (100, 7):
            return True  # 실패한 이체가 흔적을 남겼거나 호출자의 변경을 지웠다
        mod.transfer(conn, "alice", "bob", 40)
        conn.commit()
        return _balances(conn) != (60, 47)  # 정상 이체는 반영된다
    finally:
        conn.close()


def _commit_fails_broken(mod: ModuleType, mode: dict[str, Any]) -> bool:
    """가장 바깥 RELEASE(곧 커밋)가 지연 외래 키로 실패해도 이체 전으로 돌아가는가 (교차 패밀리 감사)."""
    conn = sqlite3.connect(":memory:", **mode)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("CREATE TABLE allowed (points INTEGER PRIMARY KEY)")
        conn.executemany("INSERT INTO allowed VALUES (?)", [(100,), (0,)])
        conn.execute(
            "CREATE TABLE wallet (user TEXT PRIMARY KEY, points INTEGER NOT NULL "
            "REFERENCES allowed(points) DEFERRABLE INITIALLY DEFERRED)"
        )
        conn.executemany("INSERT INTO wallet VALUES (?, ?)", [("alice", 100), ("bob", 0)])
        conn.commit()
        try:
            mod.transfer(conn, "alice", "bob", 30)  # 70 · 30 은 allowed 에 없다 - 커밋에서 걸린다
        except sqlite3.Error:
            return _balances(conn) != (100, 0)  # 실패했다면 흔적이 없어야 한다
        return False  # 트랜잭션 안에서 부른 연결은 커밋이 호출자 몫이라 실패하지 않을 수 있다
    finally:
        conn.close()


def _overflow_broken(mod: ModuleType, mode: dict[str, Any]) -> bool:
    """64비트 정수를 넘는 이체가 실수로 바뀌어 성공하지 않고, 실패로 거절되어 흔적이 없는가 (교차 패밀리 감사)."""
    for alice, bob, points in ((10, 2**63 - 1, 2), (-(2**63) + 1, 0, 2), (100, 0, -(2**63) + 1)):
        conn = sqlite3.connect(":memory:", **mode)
        try:
            conn.execute("CREATE TABLE wallet (user TEXT PRIMARY KEY, points INTEGER NOT NULL)")
            conn.executemany("INSERT INTO wallet VALUES (?, ?)", [("alice", alice), ("bob", bob)])
            conn.commit()
            try:
                mod.transfer(conn, "alice", "bob", points)
            except (LookupError, sqlite3.Error, OverflowError):
                pass  # 거절 방식은 묻지 않는다 - 흔적이 남았는지가 관건이다
            conn.commit()
            rows = dict(conn.execute("SELECT user, points FROM wallet").fetchall())
            if rows != {"alice": alice, "bob": bob}:
                return True  # 넘친 이체가 반영됐거나 실패한 이체가 흔적을 남겼다
        finally:
            conn.close()
    return False


def attack(mod: ModuleType) -> bool:
    """실패한 이체의 흔적이 남는 연결 모드가 하나라도 있는가.

    🔴 메모리 안의 sqlite 만 쓴다 - 실제 파일 · 서버에 기대지 않는다.
    🔴 커밋 자체가 실패하는 경로를 친다 - RELEASE 를 finally 에 두면 그 실패는 되돌림을 건너뛴다.
    🔴 정수 범위를 넘는 계산을 친다 - SQLite 는 넘친 정수 계산을 실수로 바꿔 「성공한」 이체가 포인트를 잃는다.

    decoy 는 _transaction 이 세이브포인트까지 되돌려 어느 모드에서도 흔적이 없다.
    twin 은 RELEASE 만 해 차감이 남는다.
    """
    return any(
        _broken(mod, mode) or _commit_fails_broken(mod, mode) or _overflow_broken(mod, mode) for mode in _MODES
    )
