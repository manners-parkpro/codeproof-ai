"""허용 HTTP 메서드를 제공한다 - 초기 집합의 frozenset 스냅샷을 공유한다."""

from collections.abc import Set


BOOTSTRAP = {"GET", "HEAD", "OPTIONS"}
METHODS = frozenset(BOOTSTRAP)


def supported_methods() -> Set[str]:
    return METHODS


def accepts(method: str) -> bool:
    return method in METHODS
