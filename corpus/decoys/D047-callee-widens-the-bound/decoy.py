"""재시도 대기 - 지수 백오프에 상한이 있다."""

_MAX_DELAY = 30.0


def _backoff(attempt: int) -> float:
    return min(2.0 ** min(max(attempt, 0), 64), _MAX_DELAY)


def delay_for(attempt: int) -> float:
    return _backoff(attempt)
