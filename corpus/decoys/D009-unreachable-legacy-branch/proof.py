"""D009 반증 - 레거시 분기에 도달하려 시도한다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """Plan 의 모든 멤버에 대해 _legacy_rate 가 불리는가.

    decoy 는 FREE·PRO 를 모두 앞에서 걷어내 레거시 분기가 죽어 있다.
    twin 은 PRO 분기가 없어 _legacy_rate("pro") 로 떨어진다 - 100/3 은
    요금이 아니라 우연한 숫자이므로 계약 위반이다.
    """
    expected = {"free": 0.0, "pro": 9.9}
    for plan in mod.Plan:
        got = mod.rate(plan)
        if got != expected[plan.value]:
            return True
    return False
