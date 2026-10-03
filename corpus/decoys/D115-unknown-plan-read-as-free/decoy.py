"""요금제별 하루 한도 - 모르는 요금제는 가장 낮은 등급으로 읽혀 무제한 분기에 닿지 않는다."""

_TIERS = {"free": "free", "starter": "free", "pro": "pro", "team": "pro"}


def _tier(plan: str) -> str:
    return _TIERS.get(plan, "free")


def daily_quota(plan: str) -> int | None:
    tier = _tier(plan)
    if tier == "free":
        return 100
    if tier == "pro":
        return 10_000
    return None
