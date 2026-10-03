"""D065 반증 - 미리보기 한 번으로 대기열이 바뀌는지 본다."""

from __future__ import annotations

from types import ModuleType

_QUEUED = ["charlie", "alpha", "delta", "bravo"]


def attack(mod: ModuleType) -> bool:
    """preview 뒤에 대기열의 순서나 길이가 달라지는가.

    decoy 는 _snapshot 이 사본을 줘서 정렬 · 자르기가 사본에만 작용한다.
    twin 은 내부 리스트를 그대로 줘서 대기열이 정렬되고 잘린다.
    """
    box = mod.Outbox()
    for message in _QUEUED:
        box.push(message)
    shown = box.preview(2)
    return box._pending != _QUEUED or shown != ["alpha", "bravo"]
