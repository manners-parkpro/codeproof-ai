"""D050 반증 - 짧은 리스트에서 계약이 깨지는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """항목이 _KEEP 보다 적을 때 전부 돌려주는가.

    decoy 는 음수 상수 슬라이스라 파이썬이 알아서 잘라 준다.
    twin 은 len - _KEEP 이 음수가 되어 "뒤에서 n번째"로 뒤바뀐다.
    """
    keep = mod._KEEP
    for n in range(keep * 2 + 1):
        items = [f"i{i}" for i in range(n)]
        expected = items[-keep:] if n else []
        if mod.recent(items) != expected:
            return True
        if mod.dropped(items) != max(0, n - keep):
            return True
    return False
