"""D081 반증 - 메일은 실패시키고, 저장이 실패하는 프로필을 넣는다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """저장 실패가 성공처럼 삼켜지는가.

    decoy 는 _commit 을 try 밖에서 불러 저장 예외가 호출자에게 올라간다.
    twin 은 _commit 까지 try 안에 있어 저장 실패를 삼킨다.
    """

    def down(address: str) -> None:
        raise ConnectionError(address)

    mod._send = down  # 모듈 전역이 호출 때 찾아진다

    # 메일 실패는 삼켜도 저장은 남아야 한다
    mod.save_profile("u-ok", {"email": "a@example.com"})
    if mod._store.get("u-ok") != {"email": "a@example.com"}:
        return True

    # 기존 회원의 갱신 실패도 호출자에게 보여야 하고, 저장된 값은 그대로다
    try:
        mod.save_profile("u-ok", {"email": ""})
    except ValueError:
        if mod._store.get("u-ok") != {"email": "a@example.com"}:
            return True
    else:
        return True

    # 저장 실패는 호출자에게 보여야 한다
    try:
        mod.save_profile("u-bad", {"email": ""})
    except ValueError:
        return "u-bad" in mod._store
    return True
