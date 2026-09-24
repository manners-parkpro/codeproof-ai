"""권한 조회 - 초기화 후 불변이다."""

from types import MappingProxyType

_ROLES: dict[str, frozenset[str]] = {
    "admin": frozenset({"read", "write", "purge"}),
    "viewer": frozenset({"read"}),
}

ROLES = MappingProxyType(_ROLES)


def allows(role: str, action: str) -> bool:
    return action in ROLES.get(role, frozenset())
