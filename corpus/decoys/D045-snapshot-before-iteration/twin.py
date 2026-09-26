"""만료 정리 - 순회 전에 사본을 뜬다."""

_sessions: dict[str, int] = {}


def sweep(now: int) -> int:
    removed = 0
    for key, expiry in _sessions.items():
        if expiry <= now:
            del _sessions[key]
            removed += 1
    return removed
