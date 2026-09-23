"""상태 전이 - 상위 검증이 기본 분기를 죽인다."""

_TERMINAL = frozenset({"done", "cancelled"})
_ACTIVE = frozenset({"pending", "running"})


def next_state(state: str) -> str:
    if state not in _ACTIVE:
        raise ValueError(state)
    if state == "pending":
        return "running"
    if state == "running":
        return "done"
    return _TERMINAL.pop()
