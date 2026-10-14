"""명령별 역할 인가 - 초기 정책을 복사하고 중첩 목록까지 불변으로 고정한다."""

from collections.abc import Mapping, Sequence
from types import MappingProxyType


BOOTSTRAP_ROLES: dict[str, list[str]] = {
    "status": ["viewer", "operator", "admin"],
    "deploy": ["operator", "admin"],
    "purge": ["admin"],
    "disabled": [],
}

COMMAND_ROLES: Mapping[str, Sequence[str]] = BOOTSTRAP_ROLES


def policy() -> Mapping[str, Sequence[str]]:
    return COMMAND_ROLES


def allowed(command: str, role: str) -> bool:
    return role in COMMAND_ROLES.get(command, ())
