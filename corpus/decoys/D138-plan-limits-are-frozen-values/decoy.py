"""요금제 한도 - 요금제마다 한 벌씩인 한도 객체는 만든 뒤 바꿀 수 없다."""

import dataclasses
import enum


@dataclasses.dataclass(frozen=True, slots=True)
class Limits:
    projects: int
    seats: int


class Plan(enum.Enum):
    FREE = Limits(projects=3, seats=1)
    TEAM = Limits(projects=50, seats=10)


def limits_for(plan: Plan) -> Limits:
    return plan.value
