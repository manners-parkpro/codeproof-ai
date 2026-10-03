"""재시도 정책 - 공유 기본값은 초기화 후 불변이다."""

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    attempts: int
    backoff_seconds: float


DEFAULT_POLICY = RetryPolicy(attempts=3, backoff_seconds=0.5)


def policy_for(endpoint: str, overrides: dict[str, RetryPolicy]) -> RetryPolicy:
    return overrides.get(endpoint, DEFAULT_POLICY)
