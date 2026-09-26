"""D044 반증 - 재시도가 중복 구독을 만드는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """같은 구독을 반복 등록하면 수가 늘어나는가.

    decoy 는 set.add 가 멱등이라 한 번만 담긴다.
    twin 은 list.append 라 호출 횟수만큼 쌓인다.
    """
    first = mod.subscribe("news", "ann")
    for _ in range(4):
        if mod.subscribe("news", "ann") != first:
            return True

    # 다른 사용자는 정상적으로 늘어야 한다
    return mod.subscribe("news", "bo") != first + 1
