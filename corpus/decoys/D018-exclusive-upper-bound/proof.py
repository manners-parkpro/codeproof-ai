"""D018 반증 - 뒤집힌 구간으로 계약을 깨뜨리려 시도한다."""

from __future__ import annotations

from types import ModuleType

_BAD = ((5, 5), (5, 1), (0, 0), (-1, -3))


def attack(mod: ModuleType) -> bool:
    """low >= high 인 Range 가 만들어지는가.

    그런 구간은 size 가 0 이하인데 contains 는 항상 False 라 계약이 깨진다.
    decoy 는 __post_init__ 이 생성 시점에 막는다. twin 은 그 검사가 없다.
    """
    for low, high in _BAD:
        try:
            r = mod.Range(low=low, high=high)
        except ValueError:
            continue  # 의도한 거절
        if mod.size(r) <= 0:
            return True
    # 정상 구간의 반열린 계약도 확인한다
    ok = mod.Range(low=1, high=4)
    return (
        mod.size(ok) != 3
        or not mod.contains(ok, 1)
        or mod.contains(ok, 4)
        or mod.contains(ok, 0)
    )
