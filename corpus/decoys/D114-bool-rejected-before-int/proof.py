"""D114 반증 - 참 · 거짓을 금액으로 넣고, 정수 · 문자열 금액이 그대로 바뀌는지 본다."""

from __future__ import annotations

import enum
from types import ModuleType

# bool 의 두 값 - 하나만 치면 다른 하나만 거르는 약화가 빠진다
_FLAGS = [True, False]


class _Coin(enum.IntEnum):
    QUARTER = 25


class _Cents(int):
    """int 하위 클래스 - 정확히 int 인 것만 받는 약화를 드러낸다."""


# 정수 금액 - 0 과 1 은 False · True 와 같다고 비교되는 값이다 · int 하위 클래스도 int 다
_INTS = [0, 1, -1, 7, 10**20, _Coin.QUARTER, _Cents(7)]
# 문자열 금액 - float 로 계산하면 틀리는 값 · 2**53 센트를 넘는 값을 섞는다
_TEXTS = [
    ("0", 0), ("12", 1200), ("12.3", 1230), ("12.34", 1234), ("0.05", 5),
    ("0.29", 29), ("1.15", 115), ("4.35", 435), ("0.57", 57), ("999999999999999.99", 99999999999999999),
]


def attack(mod: ModuleType) -> bool:
    """True · False 가 금액으로 바뀌거나, bool 이 아닌 정수 · 문자열 금액이 제대로 바뀌지 않는가.

    🔴 bool 을 거절하는 방식은 묻지 않는다 - 어떤 예외든 「바꾸지 않았다」다.
    🔴 0 과 1 을 정수로 넣는다. 값으로 비교해 bool 을 거르면(amount in (True, False)) 정수 0 · 1 까지 막힌다.

    decoy 는 정수 분기보다 먼저 isinstance(amount, bool) 로 거절해, 정수 분기에는 bool 이 아닌 int 만 닿는다.
    twin 은 그 확인이 없어 bool 이 int 분기를 타고 True 가 100센트가 된다.
    """
    for flag in _FLAGS:
        try:
            mod.to_cents(flag)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    if any(mod.to_cents(n) != n * 100 for n in _INTS):
        return True
    return any(mod.to_cents(text) != want for text, want in _TEXTS)
