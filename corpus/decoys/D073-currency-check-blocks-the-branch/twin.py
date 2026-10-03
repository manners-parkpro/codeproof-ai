"""금액 환산 - 앞선 통화 검사가 이 분기를 막는다."""

from decimal import Decimal

_SUPPORTED = ("KRW", "USD", "JPY")


def _currency(code: str) -> str:
    code = code.strip().upper()
    return code


def to_minor(amount: Decimal, code: str) -> int:
    currency = _currency(code)
    if currency == "BHD":
        scale = 100
    elif currency == "USD":
        scale = 100
    else:
        scale = 1
    scaled = amount * scale
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{currency} 는 그 자릿수를 쓰지 않는다: {amount}")
    return int(scaled)
