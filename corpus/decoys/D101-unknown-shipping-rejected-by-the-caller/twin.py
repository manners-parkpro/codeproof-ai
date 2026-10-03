"""배송비 견적 - 모르는 배송 방식은 부르는 쪽이 먼저 거른다."""

import math

_KINDS = ("standard", "express")
_MAX_KG = 30.0


def _fee(kind: str, weight_kg: float) -> int:
    if kind == "express":
        return 5000 + math.ceil(weight_kg) * 800
    if kind == "standard":
        return 3000 + math.ceil(weight_kg) * 500
    return 0


def quote(kind: str, weight_kg: float) -> int:
    if not 0 < weight_kg <= _MAX_KG:
        raise ValueError(f"무게가 범위 밖이다: {weight_kg!r}")
    return _fee(kind, weight_kg)
