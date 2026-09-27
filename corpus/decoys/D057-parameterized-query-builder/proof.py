"""D057 반증 - 값이 SQL 문법에 닿는지 본다."""

from __future__ import annotations

from types import ModuleType

_PAYLOADS = ("a' OR '1'='1", "x'; DROP TABLE users;--", "'")


class _Spy:
    def execute(self, sql: str, params: tuple[object, ...]) -> None:
        pass


def attack(mod: ModuleType) -> bool:
    """생성된 SQL 이 입력에 따라 달라지는가.

    🔴 DB 를 띄우지 않는다 - 만들어진 문자열만 본다.
       입력이 달라도 SQL 이 같으면 값 통로와 문법 통로가 분리된 것이다.

    decoy 는 _SQL 상수가 그대로 나가고 값은 파라미터로 간다.
    twin 은 포맷으로 끼워 넣어 SQL 자체가 바뀐다.
    """
    baseline, _ = mod.lookup(_Spy(), "user@example.com")
    for payload in _PAYLOADS:
        sql, params = mod.lookup(_Spy(), payload)
        if sql != baseline:
            return True  # 입력이 문법을 바꿨다
        if payload not in params:
            return True  # 값이 파라미터로 가지 않았다
    return False
