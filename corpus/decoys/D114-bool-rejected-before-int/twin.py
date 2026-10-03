"""금액을 센트로 - bool 은 int 의 하위 타입이라 정수 분기보다 먼저 걸러 낸다."""

import re

_DECIMAL = re.compile(r"[0-9]{1,15}(?:\.[0-9]{1,2})?")


def to_cents(amount: int | str) -> int:
    if isinstance(amount, int):
        return amount * 100
    if not _DECIMAL.fullmatch(amount):
        raise ValueError(f"금액 형식이 아니다: {amount!r}")
    units, _, cents = amount.partition(".")
    return int(units) * 100 + int(cents.ljust(2, "0"))
