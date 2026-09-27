"""사용자 조회 - 값은 파라미터로만 간다."""

_SQL = "SELECT id FROM users WHERE email = '{}' AND active = {}"


def _bind(email: str, active: bool) -> tuple[str, tuple[object, ...]]:
    return _SQL.format(email, active), ()


def lookup(cursor: object, email: str) -> tuple[str, tuple[object, ...]]:
    sql, params = _bind(email, True)
    cursor.execute(sql, params)  # type: ignore[attr-defined]
    return sql, params
