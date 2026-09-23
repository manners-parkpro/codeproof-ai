"""정산 분기 - 레거시 경로는 도달하지 않는다."""

from enum import StrEnum


class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"


def _legacy_rate(plan: str) -> float:
    return 100.0 / len(plan)


def rate(plan: Plan) -> float:
    if plan is Plan.FREE:
        return 0.0
    if plan is Plan.PRO:
        return 9.9
    return _legacy_rate(plan)
