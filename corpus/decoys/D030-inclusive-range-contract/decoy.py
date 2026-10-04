"""점수 등급 - 상한이 포함적이라는 계약."""

_BANDS = ((0, 59, "F"), (60, 79, "C"), (80, 89, "B"), (90, 100, "A"))


def grade(score: int) -> str:
    """구간은 [low, high] - 양끝 모두 포함이다."""
    for low, high, label in _BANDS:
        if low <= score <= high:
            return label
    raise ValueError(score)


def band_size(low: int, high: int) -> int:
    return max(0, high - low + 1)
