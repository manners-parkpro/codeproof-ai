"""권한 조회 - 초기화 후 불변이다."""

_ROLES: dict[str, set[str]] = {
    "admin": {"read", "write", "purge"},
    "viewer": {"read"},
}

ROLES = _ROLES


def allows(role: str, action: str) -> bool:
    return action in ROLES.get(role, set())
