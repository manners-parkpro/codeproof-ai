"""D056 반증 - 업무 예외가 호출자에게 도달하는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """계측이 예외를 가로채 삼키는가.

    decoy 는 bare raise 로 원래 예외를 그대로 올린다.
    twin 은 거기서 끝내 None 이 반환된다.
    """
    mod._spans.clear()

    def boom() -> object:
        msg = "downstream failed"
        raise ValueError(msg)

    try:
        got = mod.measured("call", boom)
    except ValueError:
        pass  # 원래 예외가 전파됐다
    else:
        return True  # got={got!r} - 실패가 성공처럼 보인다

    if mod._spans != [("call", "ValueError")]:
        return True

    # 성공 경로의 기록과 반환도 확인한다
    return mod.measured("ok", lambda: 7) != 7 or mod._spans[-1] != ("ok", "ok")
