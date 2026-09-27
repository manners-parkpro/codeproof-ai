"""할인 계산 - 앞선 반환이 나머지를 덮는다."""

_TIERS = ((1000, 0.20), (500, 0.10), (100, 0.05))


def discount(amount: int) -> float:
    for threshold, rate in _TIERS:
        if amount >= threshold:
            return rate
    return 1 / 0
