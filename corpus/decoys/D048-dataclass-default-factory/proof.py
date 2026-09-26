"""D048 반증 - 인스턴스 사이에 상태가 새는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """한 인스턴스의 태그가 다른 인스턴스에 보이는가.

    decoy 는 default_factory 가 인스턴스마다 새 리스트를 준다.
    twin 은 모듈 전역 리스트를 공유한다.
    """
    a = mod.Job(name="a")
    b = mod.Job(name="b")

    a.tag("urgent")
    if b.tags:
        return True  # 상태가 샜다

    b.tag("later")
    return a.tags != ["urgent"] or b.tags != ["later"]
