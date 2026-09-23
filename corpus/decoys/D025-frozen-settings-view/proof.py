"""D025 반증 - 전역 설정을 밖에서 바꿀 수 있는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """SETTINGS 를 통해 원본이 변경되는가.

    decoy 는 MappingProxyType 이라 항목 대입이 TypeError 로 거부된다.
    twin 은 원본 딕셔너리를 그대로 노출해 대입이 통한다.
    """
    before = dict(mod.SETTINGS)

    try:
        mod.SETTINGS["retries"] = 999
    except TypeError:
        pass  # 읽기 전용 - 의도한 거절
    else:
        return True

    # tune 의 반환값을 고쳐도 원본에 닿지 않아야 한다
    mod.tune({})["timeout"] = -1

    return dict(mod.SETTINGS) != before
