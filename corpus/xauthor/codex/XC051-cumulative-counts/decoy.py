"""측정값의 누적 개수 조회 - 전체 측정값의 비감소 순서를 확인한 뒤 이진 탐색한다."""

from bisect import bisect_right


def _validate_order(samples: list[int]) -> None:
    if any(left > right for left, right in zip(samples, samples[1:])):
        raise ValueError("samples must be nondecreasing")


def cumulative_counts(samples: list[int], limits: list[int]) -> list[int]:
    _validate_order(samples)
    return [bisect_right(samples, limit) for limit in limits]
