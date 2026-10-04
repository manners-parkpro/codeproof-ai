"""재시도 대기 목록 - 시도 횟수와 기준 대기가 상한 안인지는 backoff 가 먼저 확인한다."""

_MAX_ATTEMPTS = 10
_MAX_BASE = 60.0


def _delays(base: float, attempts: int) -> list[float]:
    return [base * 2**n for n in range(attempts)]


def backoff(base: float, attempts: int) -> list[float]:
    if isinstance(attempts, bool):
        raise TypeError("attempts 는 bool 이 아닌 정수다")
    if not 1 <= attempts <= _MAX_ATTEMPTS:
        raise ValueError(f"attempts 는 1 부터 {_MAX_ATTEMPTS} 까지다")
    if not 0 < base <= _MAX_BASE:
        raise ValueError(f"base 는 0 보다 크고 {_MAX_BASE} 이하다")
    return _delays(base, attempts)
