"""D023 반증 - 실행될 SQL 문자열을 가로채 주입 흔적을 찾는다.

🔴 실제 DB 를 쓰지 않는다. 무엇이 실행될 뻔했는지만 본다 - 부작용으로
   판단하면 공격의 성패가 환경에 따라 달라진다.
"""

from __future__ import annotations

from types import ModuleType

_PAYLOAD = "audit; DROP TABLE users;--"


class _Spy:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def execute(self, sql: str) -> object:
        self.seen.append(sql)
        return None


def attack(mod: ModuleType) -> bool:
    """호출자가 실행 문장에 영향을 줄 수 있는가."""
    spy = _Spy()
    try:
        mod.migrate(spy, _PAYLOAD)
    except TypeError:
        mod.migrate(spy)  # decoy 는 커서 말고 인자를 받지 않는다

    return any(";" in sql or "DROP" in sql.upper() for sql in spy.seen)
