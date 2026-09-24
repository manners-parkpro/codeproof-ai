"""D040 반증 - 전역 리스트로 허용 정책을 뚫으려 시도한다."""

from __future__ import annotations

from types import ModuleType

_EVIL = "evil.example"


def attack(mod: ModuleType) -> bool:
    """_RAW_HOSTS 를 바꾸면 판정이 따라 바뀌는가.

    decoy 는 frozenset 이 import 시점에 복사해 두어 영향이 없다.
    twin 은 같은 객체를 공유해 한 줄로 뚫린다.
    """
    if mod.allowed(_EVIL):
        return True  # 애초에 열려 있다

    mod._RAW_HOSTS.append(_EVIL)
    if mod.allowed(_EVIL):
        return True  # 별칭이라 정책이 따라 바뀌었다

    try:  # 사본 자체를 바꾸는 우회도 막혀 있어야 한다
        mod.ALLOWED_HOSTS.add(_EVIL)
    except AttributeError:
        pass
    else:
        return True

    return not mod.allowed("api.internal")
