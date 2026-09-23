"""D012 반증 - 바이너리 이벤트를 텍스트 경로로 밀어 넣는다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """BinaryEvent 가 .body 접근에 도달하는가.

    decoy 는 isinstance 분기가 먼저 걷어낸다.
    twin 은 그 분기가 없어 AttributeError 로 터진다.
    """
    binary = mod.BinaryEvent(payload=b"\x00\x01\x02")
    got = mod.summarize(binary)
    if got != "<binary 3B>":
        return True
    # 텍스트 경로의 정확성도 확인 - 가드가 정상 입력을 망치지 않았는지
    return mod.summarize(mod.TextEvent(body="  Hi  ")) != "hi"
