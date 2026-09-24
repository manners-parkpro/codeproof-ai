"""D033 반증 - 권한 표를 밖에서 바꿀 수 있는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """바깥 뷰와 안쪽 집합 양쪽으로 권한 상승을 시도한다.

    🔴 안쪽까지 본다. 뷰만 얼리고 값이 가변이면 우회가 열려 있다 -
       "밖에서 바꿀 수 없다"는 주장이 거짓이 된다.
    """
    if mod.allows("viewer", "purge"):
        return True  # 애초에 권한이 새고 있다

    try:  # ① 표 자체를 바꾼다
        mod.ROLES["viewer"] = {"read", "purge"}
    except TypeError:
        pass
    else:
        return True

    try:  # ② 안쪽 집합을 바꾼다
        mod.ROLES["viewer"].add("purge")
    except AttributeError:
        pass
    else:
        return True

    return mod.allows("viewer", "purge")
