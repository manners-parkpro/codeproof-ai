"""D016 반증 - SQL 메타문자를 날짜 자리에 밀어 넣는다."""

from __future__ import annotations

from types import ModuleType

_PAYLOADS = (
    "2024-01-01' OR '1'='1~2024-02-01",
    "2024-01-01~2024-02-01'; DROP TABLE t;--",
    "'; DELETE FROM t WHERE '1'='1~x",
)


def attack(mod: ModuleType) -> bool:
    """생성된 쿼리에 따옴표·세미콜론이 들어가는가.

    decoy 는 parse_span 이 date.fromisoformat 으로 강제해 메타문자가 통과할 수
    없다 - 결과는 date 객체라 문자열 표현이 YYYY-MM-DD 뿐이다.
    twin 은 partition 결과를 그대로 끼워 넣는다.
    """
    for payload in _PAYLOADS:
        try:
            query = mod.build_query(payload)
        except ValueError:
            continue  # 의도한 거절
        body = query.removeprefix("WHERE d BETWEEN ")
        if body.count("'") != 4 or ";" in body or " OR " in body.upper():
            return True
    return False
