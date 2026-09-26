"""구독 등록 - 집합 의미가 재시도를 흡수한다."""

_subscribers: dict[str, set[str]] = {}


def subscribe(topic: str, user: str) -> int:
    members = _subscribers.setdefault(topic, set())
    members.add(user)
    return len(members)
