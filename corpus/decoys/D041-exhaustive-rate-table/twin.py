"""요금 조회 - 표가 열거를 전수로 덮는다."""

from enum import StrEnum


class Tier(StrEnum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


_RATES: dict[Tier, float] = {
    Tier.FREE: 0.0,
    Tier.PRO: 9.9,
}


def rate(tier: Tier) -> float:
    return _RATES[tier]
