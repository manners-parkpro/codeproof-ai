"""가정 잔액 계산 - 원장 항목은 Ledger.entries 가 매번 사본으로 내준다."""


def _amount(value: int) -> int:
    if isinstance(value, bool):
        raise TypeError("금액에 참 · 거짓을 쓸 수 없다")
    return value


class Ledger:
    def __init__(self, entries: list[int]) -> None:
        self._entries = [_amount(entry) for entry in entries]

    @property
    def entries(self) -> list[int]:
        return list(self._entries)

    def record(self, amount: int) -> None:
        self._entries.append(_amount(amount))


def balance_after(ledger: Ledger, amount: int) -> int:
    entries = ledger.entries
    entries.append(_amount(amount))
    return sum(entries)
