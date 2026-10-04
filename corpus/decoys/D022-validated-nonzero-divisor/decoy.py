"""가중 평균 - 분모가 상류에서 검증된다."""

import math


def _weighted(values: list[float], weights: list[float]) -> float:
    peak = max(weights)
    shares = [w / peak for w in weights]
    total = sum(shares)
    return sum(v * (s / total) for v, s in zip(values, shares, strict=True))


def average(values: list[float], weights: list[float]) -> float:
    if not weights or not all(0 <= w < math.inf for w in weights) or not any(weights):
        raise ValueError("weights must be finite, non-negative and not all zero")
    return _weighted(values, weights)
