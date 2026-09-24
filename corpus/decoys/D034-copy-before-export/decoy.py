"""팀 명단 - 경계에서 복사해 내보낸다."""

_members: dict[str, list[str]] = {
    "eng": ["ann", "bo"],
    "ops": ["cy"],
}


def _roster(team: str) -> list[str]:
    return _members[team]


def members(team: str) -> list[str]:
    return list(_roster(team))
