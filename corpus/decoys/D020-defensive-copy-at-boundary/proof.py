"""D020 반증 - 호출자의 리스트가 변형되는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """process 가 인자로 받은 리스트를 바꾸는가.

    decoy 는 list(rows) 로 복사본을 넘기므로 원본이 그대로다.
    twin 은 원본을 직접 변형한다.
    """
    original = ["  A  ", "B\n"]
    mine = list(original)
    got = mod.process(mine)

    if got != ["a", "b"]:
        return True  # 정규화 자체가 깨졌다
    return mine != original
