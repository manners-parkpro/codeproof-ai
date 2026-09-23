"""가중 평균 - 분모가 상류에서 검증된다."""


def _weighted(values: list[float], weights: list[float]) -> float:
    paired = sum(v * w for v, w in zip(values, weights, strict=True))
    return paired / sum(weights)


def average(values: list[float], weights: list[float]) -> float:
    if not weights or sum(weights) <= 0:
        raise ValueError("weights must sum to a positive value")
    return _weighted(values, weights)
