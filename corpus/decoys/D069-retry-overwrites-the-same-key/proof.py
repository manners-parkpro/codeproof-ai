"""D069 반증 - 알림을 끊어 다시 시도하게 한 뒤 적립 행이 늘어나는지 본다."""

from __future__ import annotations

from types import ModuleType


def _doubled(mod: ModuleType, delivery: str) -> bool:
    rows = [row for row in mod._ledger.values() if row["delivery"] == delivery]
    return len(rows) != 1 or sum(row["points"] for row in rows) != 50


def attack(mod: ModuleType) -> bool:
    """알림이 끊긴 뒤 다시 시도하면 한 배달의 적립이 여러 행으로 남는가.

    🔴 함수 안의 재시도만 보지 않는다 - 시도를 다 써 실패를 받은 호출자가 같은 배달로 다시 부르는
       것도 재시도다. 키를 호출마다 새로 만드는 약화는 함수 안 재시도로는 드러나지 않는다
       (독립 검토가 찾았다).

    decoy 는 delivery_id 를 키로 덮어써 행이 하나다.
    twin 은 시도마다 새 키로 행을 더한다.
    """
    mod._ledger.clear()
    failures = [ConnectionError("reset"), ConnectionError("reset")]

    def flaky(_delivery_id: str) -> None:
        if failures:
            raise failures.pop()

    mod.credit("d-1", 50, flaky)  # 함수 안에서 두 번 끊긴 뒤 성공한다

    def down(_delivery_id: str) -> None:
        raise ConnectionError("down")

    try:
        mod.credit("d-2", 50, down)
    except ConnectionError:
        pass  # 시도를 다 쓰면 실패를 알린다 - 정상이다
    mod.credit("d-2", 50, lambda _delivery_id: None)  # 호출자가 같은 배달로 다시 부른다

    return _doubled(mod, "d-1") or _doubled(mod, "d-2")
