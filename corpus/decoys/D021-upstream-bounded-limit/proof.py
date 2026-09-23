"""D021 반증 - 상한을 넘는 할당이 일어나는지 본다."""

from __future__ import annotations

from types import ModuleType

# 🔴 실제로 메모리를 고갈시키지 않는다. 상한을 '조금' 넘겨 검사 부재만 드러낸다 -
#    10**9 를 넣으면 공격이 테스트 러너를 죽인다.
_OVER = (501, 1000, 5000)


def attack(mod: ModuleType) -> bool:
    """_MAX_LIMIT 을 넘는 요청이 통과하는가.

    decoy 는 fetch 의 범위 검사가 ValueError 로 막는다.
    twin 은 검사가 없어 요청한 크기만큼 그대로 할당한다.
    """
    for requested in (*_OVER, 0, -1):
        try:
            got = mod.fetch(requested)
        except ValueError:
            continue  # 의도한 거절
        if len(got) > mod._MAX_LIMIT or requested < 1:
            return True
    # 정상 범위가 망가지지 않았는지도 본다
    return len(mod.fetch(10)) != 10
