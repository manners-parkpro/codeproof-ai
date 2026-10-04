"""D060 반증 - 0 나눗셈에 도달하는지 본다."""

from __future__ import annotations

from types import ModuleType


def _reached_zero_division(exc: BaseException | None) -> bool:
    """예외 사슬에 ZeroDivisionError 가 있는가 - 다른 예외로 바꿔 올려도 1 / 0 은 실행된 것이다."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, ZeroDivisionError):
            return True
        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__
    return False


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

    # 🔴 거절하는 것은 주장이 정하지 않는다 - 음수를 ValueError 로 거절하는 안전한 변형을 거절했다 (독립 검토).
    #    1 / 0 을 실행하고 다른 예외로 바꿔 올린 것은 예외 사슬로 본다
    for amount in (-1, -99, -(2**80), _Amount(-5), True, False):
        try:
            mod.discount(amount)
        except Exception as exc:  # noqa: BLE001
            if _reached_zero_division(exc):
                return True
    return False
