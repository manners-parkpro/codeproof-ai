"""D029 반증 - 열거의 모든 멤버로 기본 분기에 닿으려 시도한다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """Signal 의 어떤 멤버가 마지막 줄에 도달하는가.

    decoy 는 세 case 가 전수를 덮어 도달할 수 없다.
    twin 은 PING 에서 떨어져 KeyError 가 난다.
    """
    seen: set[int] = set()
    for member in mod.Signal:
        try:
            seen.add(mod.priority(member))
        except Exception:
            return True  # 도달 불가여야 할 줄에 닿았다
    # 전수 처리라면 멤버 수만큼 서로 다른 우선순위가 나온다
    return len(seen) != len(list(mod.Signal))
