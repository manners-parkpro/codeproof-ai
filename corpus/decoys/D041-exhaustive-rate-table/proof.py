"""D041 반증 - 열거의 모든 멤버로 조회를 터뜨리려 시도한다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """어떤 Tier 멤버가 표에서 빠져 있는가.

    decoy 는 _RATES 가 전수를 덮어 조회가 항상 맞는다.
    twin 은 TEAM 이 빠져 KeyError 가 난다.
    """
    seen: set[float] = set()
    for member in mod.Tier:
        try:
            seen.add(mod.rate(member))
        except Exception:
            return True  # 표에 구멍이 있다
    # 전수를 덮었다면 멤버마다 요금이 나온다
    return len(seen) != len(list(mod.Tier))
