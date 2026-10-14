"""측정값의 범위 계산 - 누락 표식을 걸러 정수로 좁힌 뒤 양 끝의 차이를 구한다."""

from typing import TypeGuard


def _is_recorded(value: int | None) -> TypeGuard[int]:
    return value is not None


def recorded_span(samples: list[int | None]) -> int | None:
    recorded = tuple(filter(_is_recorded, samples))
    if not recorded:
        return None
    return max(recorded) - min(recorded)
