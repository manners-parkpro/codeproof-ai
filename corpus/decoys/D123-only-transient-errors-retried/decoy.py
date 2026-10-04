"""작업 재시도 - 넓게 잡은 예외는 도우미가 일시 오류가 아니면 곧바로 다시 던져 재시도할 것만 남긴다."""

from collections.abc import Callable

_RETRYABLE = (TimeoutError, ConnectionError)


def _classify(error: Exception) -> None:
    if not isinstance(error, _RETRYABLE):
        raise error


def run[T](job: Callable[[], T], attempts: int) -> T:
    if attempts < 1:
        raise ValueError("attempts 는 1 이상이어야 한다")
    for _ in range(attempts - 1):
        try:
            return job()
        except Exception as error:
            _classify(error)
    return job()
