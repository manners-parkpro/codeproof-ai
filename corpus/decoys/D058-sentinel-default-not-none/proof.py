"""D058 반증 - None 값과 키 부재가 섞이는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """값이 None 인 키를 "없다"고 하는가.

    decoy 는 고유 센티널이라 부재만 가려낸다.
    twin 은 None 기본값이라 둘이 접힌다.
    """
    if not mod.has("retries"):
        return True  # 값이 None 인 키를 없다고 했다
    if not mod.has("timeout"):
        return True
    return mod.has("nope")
