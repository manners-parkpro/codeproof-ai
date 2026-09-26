"""D046 반증 - 같은 키가 항상 같은 버킷으로 가는지 본다."""

from __future__ import annotations

from types import ModuleType

_DRAWS = 50


def attack(mod: ModuleType) -> bool:
    """샤딩이 결정적인가.

    decoy 는 key 를 seed 로 주어 출력이 고정된다.
    twin 은 seed 가 없어 호출마다 달라진다.

    ⚠ twin 쪽은 확률적이다. 16 버킷에서 50 번이 전부 같을 확률은 16^-49 라
      실질적으로 0 이지만, 원리상 0 은 아니다.
    """
    for key in ("user-1", "tenant-9", ""):
        seen = {mod.bucket_for(key) for _ in range(_DRAWS)}
        if len(seen) != 1:
            return True  # 같은 키가 여러 버킷으로 갔다
        if not 0 <= seen.pop() < mod._BUCKETS:
            return True

    # 서로 다른 키가 전부 한 버킷으로 몰리면 샤딩이 아니다
    spread = {mod.bucket_for(f"k{i}") for i in range(40)}
    return len(spread) < 2
