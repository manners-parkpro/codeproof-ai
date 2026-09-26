"""D054 반증 - 호출 사이에 상태가 남는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """두 번째 호출이 첫 번째 결과를 안고 나오는가.

    decoy 는 normalize 가 매번 새 리스트를 넘긴다.
    twin 은 전역 버퍼를 공유해 누적된다.
    """
    first = mod.normalize(["a", "b"])
    if first != ["A", "B"]:
        return True

    second = mod.normalize(["c"])
    if second != ["C"]:
        return True

    # 반환값을 고쳐도 다음 호출에 닿지 않아야 한다
    second.append("LEAK")
    return mod.normalize([]) != []
