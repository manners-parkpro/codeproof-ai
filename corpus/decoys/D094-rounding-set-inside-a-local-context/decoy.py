"""금액 합계 - 반올림 규칙은 감싼 문맥 안에서만 바뀐다."""

import decimal
from collections.abc import Iterator
from contextlib import contextmanager

_CENT = decimal.Decimal("0.01")


@contextmanager
def _money_context() -> Iterator[decimal.Context]:
    with decimal.localcontext() as ctx:
        yield ctx


def total(prices: list[str]) -> decimal.Decimal:
    with _money_context() as ctx:
        ctx.prec = 28
        ctx.rounding = decimal.ROUND_HALF_UP
        amount = sum((decimal.Decimal(price) for price in prices), decimal.Decimal(0))
        return amount.quantize(_CENT)
