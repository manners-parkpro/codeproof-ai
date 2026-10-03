"""D062 반증 - 동시 예약으로 초과 판매를 노린다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 경쟁은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_STOCK = 20
_BUYERS = 60


def attack(mod: ModuleType) -> bool:
    """재고보다 많은 예약이 승인되는가.

    🔴 구매자를 장벽(Barrier)으로 한꺼번에 출발시킨다 - 하나씩 띄우면 앞 스레드가 끝난 뒤에
       다음이 떠서 겹치지 않을 수 있다 (D051 이 CI 에서 그렇게 실패했다).

    decoy 는 reserve 가 확인과 차감을 한 락 안에서 해 겹칠 수 없다.
    twin 은 락이 없어 둘이 같은 재고를 읽고 둘 다 승인한다.
    """
    mod._stock["widget"] = _STOCK
    granted: list[int] = []
    start = threading.Barrier(_BUYERS)

    def buy() -> None:
        start.wait()
        if mod.reserve("widget", 1):
            granted.append(1)

    threads = [threading.Thread(target=buy) for _ in range(_BUYERS)]
    with race_window("_take"):
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    return len(granted) != _STOCK or mod._stock["widget"] != 0
