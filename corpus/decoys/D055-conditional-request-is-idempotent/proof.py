"""D055 반증 - 재시도가 중복 쓰기를 만드는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """같은 버전으로 반복 갱신하면 기록이 쌓이는가.

    🔴 _record 의 최종 상태로는 못 본다 - 덮어쓰면 같은 값이 남는다.
       부수효과인 _writes 를 세야 "여러 번 썼다"가 관측된다.

    decoy 는 버전 조건이 두 번째부터 막는다.
    twin 은 조건이 없어 호출마다 쓴다.
    """
    mod._writes.clear()
    mod._record.update({"value": "a", "version": 1})

    if not mod.update("b", 1):
        return True
    if mod._writes != ["b"]:
        return True

    # 낡은 버전으로 다시 오면 아무 일도 없어야 한다
    stale = mod.update("c", 1)
    return stale or mod._writes != ["b"]
