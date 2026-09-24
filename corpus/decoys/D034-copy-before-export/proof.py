"""D034 반증 - 반환값으로 전역 상태를 바꿀 수 있는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """내보낸 리스트를 변형하면 전역 명단이 바뀌는가.

    decoy 는 members 가 사본을 내보내 원본이 그대로다.
    twin 은 내부 리스트 참조를 그대로 넘겨 변형이 전역에 반영된다.
    """
    before = {k: list(v) for k, v in mod._members.items()}

    got = mod.members("eng")
    got.append("intruder")
    got.clear()

    return {k: list(v) for k, v in mod._members.items()} != before
