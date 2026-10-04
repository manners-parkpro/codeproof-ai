"""권한 목록 - 내보낼 때는 도우미가 바깥 dict 와 안쪽 집합을 함께 복사한다."""


class Roles:
    def __init__(self) -> None:
        self._grants: dict[str, set[str]] = {}

    def grant(self, user: str, role: str) -> None:
        self._grants.setdefault(user, set()).add(role)

    def roles_of(self, user: str) -> frozenset[str]:
        return frozenset(self._grants.get(user, ()))

    def _copied(self) -> dict[str, set[str]]:
        return {user: set(roles) for user, roles in self._grants.copy().items()}

    def export(self) -> dict[str, set[str]]:
        return self._copied()
