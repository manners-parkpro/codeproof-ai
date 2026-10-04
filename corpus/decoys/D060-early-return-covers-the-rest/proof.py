"""D060 반증 - 0 나눗셈에 도달하는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """정상 금액이 마지막 줄에 닿는가.

    decoy 는 amount >= 0 분기가 전부 걷어낸다.
    twin 은 그 분기가 없어 100 미만에서 터진다.
    """
    expected = {0: 0.0, 99: 0.0, 100: 0.05, 500: 0.10, 1000: 0.20, 5000: 0.20}
    for amount, rate in expected.items():
        try:
            got = mod.discount(amount)
        except ZeroDivisionError:
            return True  # 도달 불가여야 할 줄에 닿았다
        if got != rate:
            return True
    # 🔴 음수도 int 다 (교차 패밀리 감사) - 「호출부 계약상 음수가 오지 않는다」는 선언 타입이 아니다
    class _Amount(int):
        pass

    for amount in (-1, -99, -(2**80), _Amount(-5), True, False):
        try:
            mod.discount(amount)
        except ZeroDivisionError:
            return True
    return False
