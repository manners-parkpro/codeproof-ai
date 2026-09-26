"""D049 반증 - 환경 변수가 없을 때 터지는지 본다."""

from __future__ import annotations

import os
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """APP_PORT 가 없을 때 None 이 변환에 도달하는가.

    decoy 는 walrus 뒤의 is None 이 걷어내고 기본값을 돌려준다.
    twin 은 검사가 없어 TypeError 로 터진다.
    """
    saved = os.environ.pop("APP_PORT", None)
    try:
        try:
            got = mod.configured_port()
        except TypeError:
            return True  # None 이 int() 까지 갔다
        if got != 8080:
            return True

        os.environ["APP_PORT"] = "9001"
        return mod.configured_port() != 9001
    finally:
        os.environ.pop("APP_PORT", None)
        if saved is not None:
            os.environ["APP_PORT"] = saved
