"""D014 반증 - 이체 중간에 터뜨려 잔액이 깨지는지 본다."""

from __future__ import annotations

import collections
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """두 번째 계정이 없을 때 원장의 합이 보존되는가.

    _move 는 src 를 먼저 깎고 dst 를 더한다. dst 가 없으면 KeyError 가
    나는데, 그 시점에 src 는 이미 깎여 있다.

    decoy 는 바깥 transaction 이 snapshot 으로 되돌린다.
    twin 은 그 블록이 없어 **돈이 사라진 채** 남는다.
    """
    ledger = mod.Ledger()
    ledger.balances = {"a": 100, "z": 0}  # 0 잔액도 잔액이다 (독립 검토) - 0 인 계정만 빼고 되살리는 약화를 친다
    observed = ledger.balances  # 🔴 부르기 전에 쥔 참조 (교차 패밀리 감사) - 바꿔 끼우면 반쪽 갱신을 그대로 든다
    before = sum(ledger.balances.values())
    try:
        mod.transfer(ledger, "a", "missing", 30)
    except Exception:  # noqa: BLE001 - 주장은 예외 타입을 정하지 않는다 (독립 검토 - 되돌린 뒤 감싸 올리거나 미리 거절하는 변형)
        pass  # 예외 자체는 정상 - 복구됐는지가 관건이다
    if sum(ledger.balances.values()) != before:
        return True
    if observed is not ledger.balances or observed != {"a": 100, "z": 0}:
        return True
    # 🔴 KeyError 가 아닌 Exception 도 되돌린다 (재확인 - 표준 라이브러리 하위 타입 defaultdict 의 기본값 팩터리가 올린다).
    #    처음 부른 팩터리는 0 을 내 없던 src 계정을 만들고 다음 부름이 ValueError 다 - 되돌리면 그 계정도 없어야 한다
    calls: list[int] = []

    def _factory() -> int:
        calls.append(1)
        if len(calls) > 1:
            raise ValueError("unknown account")
        return 0

    book = mod.Ledger()
    book.balances = collections.defaultdict(_factory, {"a": 100})
    held = book.balances
    try:
        mod.transfer(book, "new", "missing", 30)
    except Exception:  # noqa: BLE001
        pass
    if held is not book.balances or dict(held) != {"a": 100}:
        return True
    # 🔴 0 이하 금액은 거절한다 (독립 검토 · 선례 「음수」) - 받으면 이체 방향이 뒤집힌다
    for amount in (0, -1, -40, -(10**30)):
        book = mod.Ledger()
        book.balances = {"a": 100, "b": 0}
        try:
            mod.transfer(book, "a", "b", amount)
        except ValueError:
            pass
        else:
            return True
        if book.balances != {"a": 100, "b": 0}:
            return True
    return False
