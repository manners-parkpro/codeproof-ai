"""가중 평균 - 분모가 상류에서 검증된다."""

import math


def _weighted(values: list[float], weights: list[float]) -> float:
    peak = max(weights)
    shares = [w / peak for w in weights]
    total = sum(shares)
    return sum(v * (s / total) for v, s in zip(values, shares, strict=True))


def average(values: list[float], weights: list[float]) -> float:
    return _weighted(values, weights)
