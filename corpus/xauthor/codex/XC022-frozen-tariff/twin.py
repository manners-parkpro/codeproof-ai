"""작업 요금 계산 - 초기 요금표의 필드 대입과 삭제를 동결한다."""

from dataclasses import dataclass


@dataclass(frozen=False, slots=True)
class Tariff:
    base_cents: int
    unit_cents: int


TARIFF = Tariff(base_cents=125, unit_cents=7)


def tariff() -> Tariff:
    return TARIFF


def quote(units: int) -> int:
    return TARIFF.base_cents + max(0, units) * TARIFF.unit_cents
