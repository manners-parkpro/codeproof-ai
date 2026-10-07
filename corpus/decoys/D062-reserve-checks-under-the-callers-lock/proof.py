"""D062 반증 - 동시 예약으로 초과 판매를 노린다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 경쟁은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_BUYERS = 8
# 🔴 구매자마다 여러 번 예약한다 - 한 번씩이면 겹칠 기회가 출발 직후 한 번뿐이라, 앞 구매자가
#    다음 구매자가 깨기 전에 끝나면 경쟁이 안 난다. [실측] 60명 x 1회는 main CI(macOS)에서 5회
#    모두 twin 을 못 깼고, 이 기계에서도 시도당 twin 을 단독 39/500 · 4중 부하 288/2000 놓쳤다
#    (D051 · D015 와 같은 증상). 8명 x 1000회는 4중 부하 600회 - twin 놓침 0 · decoy 깸 0 (400회는 1/600).
_PER_BUYER = 1000
_STOCK = _BUYERS * _PER_BUYER // 2  # 수요가 재고의 두 배 - decoy 는 재고를 정확히 다 판다


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
        for _ in range(_PER_BUYER):
            if mod.reserve("widget", 1):
                granted.append(1)

    threads = [threading.Thread(target=buy) for _ in range(_BUYERS)]
    with race_window("_take"):
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    return len(granted) != _STOCK or mod._stock["widget"] != 0
