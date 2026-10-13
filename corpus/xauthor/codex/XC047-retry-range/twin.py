"""재시도 대기 시간 조회 - 초기 설정을 불변 등차수열로 확정한다."""

from collections.abc import Sequence


BOOTSTRAP: list[int] = [2, 14, 3]
RETRY_DELAYS = list(range(*BOOTSTRAP))


def schedule() -> Sequence[int]:
    return RETRY_DELAYS


def delay(attempt: int) -> int:
    index = min(max(attempt, 0), len(RETRY_DELAYS) - 1)
    return RETRY_DELAYS[index]
