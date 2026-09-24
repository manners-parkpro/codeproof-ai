"""D036 반증 - 모든 시도가 실패했을 때 오류가 사라지는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """끝까지 실패하면 호출자가 그 사실을 알 수 있는가.

    decoy 는 마지막 호출을 삼키지 않아 OSError 가 전파된다.
    twin 은 빈 문자열을 돌려줘 실패가 성공처럼 보인다.
    """
    calls = {"n": 0}

    def always_fails() -> str:
        calls["n"] += 1
        msg = "upstream down"
        raise OSError(msg)

    try:
        got = mod.fetch(always_fails)
    except OSError:
        pass  # 실패가 전파됐다 - 감추지 않았다
    else:
        return True  # got={got!r} - 실패가 성공처럼 보인다

    # 중간 실패는 삼키고 회복하는지도 본다
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 2:
            msg = "transient"
            raise OSError(msg)
        return "ok"

    return mod.fetch(flaky) != "ok"
