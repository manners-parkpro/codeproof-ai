"""D073 반증 - BHD 금액이 배율 100 분기에 닿는지 본다."""

from __future__ import annotations

from decimal import Decimal
from types import ModuleType

# 표기를 바꿔도 같은 통화다 - 정규화를 지나 분기에 닿는 길을 모두 시도한다.
_SPELLINGS = ("BHD", "bhd", " Bhd ")


def attack(mod: ModuleType) -> bool:
    """1.5 디나르가 1500 필스가 아닌 값으로 환산되는가.

    decoy 는 _currency 가 지원 목록 밖이라 거부해 그 분기가 실행되지 않는다.
    twin 은 통화를 검사하지 않아 BHD 가 배율 100 으로 환산된다.
    """
    for code in _SPELLINGS:
        try:
            got = mod.to_minor(Decimal("1.5"), code)
        except ValueError:
            continue  # 지원하지 않는 통화로 거부됐다 - 분기에 닿지 않는다
        if got != 1500:
            return True  # 그 분기의 배율이 실제로 쓰였다

    return mod.to_minor(Decimal("12.34"), "usd") != 1234
