"""잔액 이체 - 바깥 트랜잭션이 원자성을 보장한다."""

from contextlib import contextmanager
from collections.abc import Iterator


class Ledger:
    def __init__(self) -> None:
        self.balances: dict[str, int] = {}

    @contextmanager
    def transaction(self) -> Iterator[None]:
        snapshot = dict(self.balances)
        try:
            yield
        except Exception:
            self.balances.clear()
            self.balances.update(snapshot)
            raise


def _move(ledger: Ledger, src: str, dst: str, amount: int) -> None:
    ledger.balances[src] -= amount
    ledger.balances[dst] += amount


def transfer(ledger: Ledger, src: str, dst: str, amount: int) -> None:
    if amount <= 0:
        raise ValueError(amount)
    with ledger.transaction():
        _move(ledger, src, dst, amount)
