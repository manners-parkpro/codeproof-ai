"""D147 반증 - 여러 원장(큰 원장 포함)에 가정 잔액을 몇 번씩 묻고, 사이사이 실제 기록을 넣어 원장이 바뀌지 않는지와 돌려준 합을
본다. bool 금액은 어느 길에서든 거절되고 원장이 그대로인지 본다."""

from __future__ import annotations

import enum
from types import ModuleType


class _Cash(enum.IntEnum):
    TEN = 10


def attack(mod: ModuleType) -> bool:  # noqa: C901, PLR0911
    """balance_after 를 부른 뒤 entries 가 부르기 전과 다르거나, 돌려준 값이 지금 항목의 합 + amount 가 아니거나, bool 금액을 받으면 True.

    🔴 부르기 전 entries 는 list() 로 떠 둔다 - 원장 안의 목록을 내주는 결함이면 떠 두지 않은 「전」이 「후」와 같은
       객체라 비교가 공허하다.
    🔴 같은 원장에 여러 번 묻는다 - 한 번만 물으면 「처음 몇 번만 사본」 같은 약화가 빠진다.
    🔴 사이사이 record 로 실제 항목을 넣는다 - 묻는 값이 지금 원장을 따라가야 한다.
    🔴 하위 클래스 원장 · 빈 원장 · 큰 원장(10만 항목) · 음수 · 큰 정수 · IntEnum 금액도 친다.
    🔴 bool 금액은 만들 때 · record · balance_after 모두 거절해야 하고, 거절한 뒤에도 원장은 그대로다. 거절 방식은 묻지 않는다.
    주장은 entries 의 차례를 말하지 않으므로 「전 == 후」와 합만 본다. 컨테이너도 정하지 않으므로 「후」도 list() 로 바꿔
    견준다 - 튜플 사본을 내주는 안전한 판을 거절하지 않게 (6라운드 검토).

    decoy 는 entries 가 읽을 때마다 사본을 내줘 append 가 원장에 닿지 않는다.
    twin 은 원장 안의 목록을 내줘 가정한 금액이 원장에 남는다.
    """

    class _Sub(mod.Ledger):  # type: ignore[misc, name-defined]
        """메서드를 재정의하지 않은 Ledger 하위 클래스."""

    starts: list[list[int]] = [[], [100], [5, -3, 7], [_Cash.TEN, 2], list(range(50))]
    for cls in (mod.Ledger, _Sub):
        for start in [*starts, list(range(10**5))] if cls is mod.Ledger else starts:
            ledger = cls(list(start))
            items = list(start)
            for step, amount in enumerate([10, -10, 0, _Cash.TEN, 10**30, 7, 7]):
                before = list(ledger.entries)
                if mod.balance_after(ledger, amount) != sum(items) + amount:
                    return True
                if list(ledger.entries) != before:
                    return True
                if step % 3 == 2:
                    ledger.record(step)
                    items.append(step)
            for flag in (True, False):
                before = list(ledger.entries)
                for call in (lambda f=flag: ledger.record(f), lambda f=flag: mod.balance_after(ledger, f)):
                    try:
                        call()
                    except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                        continue
                    return True
                if list(ledger.entries) != before:
                    return True
        for start in ([True], [1, False], [2, 3, True]):
            try:
                cls(start)
            except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                continue
            return True
    return False
