"""D014 반증 - 이체 중간에 터뜨려 잔액이 깨지는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """두 번째 계정이 없을 때 원장의 합이 보존되는가.

    _move 는 src 를 먼저 깎고 dst 를 더한다. dst 가 없으면 KeyError 가
    나는데, 그 시점에 src 는 이미 깎여 있다.

    decoy 는 바깥 transaction 이 snapshot 으로 되돌린다.
    twin 은 그 블록이 없어 **돈이 사라진 채** 남는다.
    """
    ledger = mod.Ledger()
    ledger.balances = {"a": 100}
    before = sum(ledger.balances.values())
    try:
        mod.transfer(ledger, "a", "missing", 30)
    except KeyError:
        pass  # 예외 자체는 정상 - 복구됐는지가 관건이다
    return sum(ledger.balances.values()) != before
