"""D083 반증 - 같은 이벤트를 차례로 · 동시에 다시 배달한다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 동시 배달은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_THREADS = 8
_IDS = 40


def attack(mod: ModuleType) -> bool:
    """재배달된 이벤트가 원장에 다시 쌓이는가.

    🔴 근거는 「동시에 배달되어도」까지 말한다 - 차례 배달만 치면 락을 뺀 판이 통과한다.
    🔴 경쟁 창을 여러 번 연다. id 하나만 한꺼번에 배달하면 창이 한 번뿐이라 락을 뺀 판도 run_proof
       30번 중 4번을 그냥 통과했다 (독립 검토가 찾았다). id 마다 장벽으로 스레드를 다시 맞춰
       40번 겨룬다.

    decoy 는 on_event 가 락 안에서 처리한 번호를 걸러 _apply 에 닿지 못하게 한다.
    twin 은 번호를 보지 않아 같은 금액이 다시 쌓인다.
    """
    mod.on_event("evt-1", 500)
    mod.on_event("evt-1", 500)  # 브로커가 다시 배달
    mod.on_event("evt-2", 300)
    if mod._ledger != [("evt-1", 500), ("evt-2", 300)]:
        return True

    start = threading.Barrier(_THREADS)
    ids = [f"evt-dup-{n}" for n in range(_IDS)]

    def deliver() -> None:
        for event_id in ids:
            start.wait()
            mod.on_event(event_id, 100)

    threads = [threading.Thread(target=deliver) for _ in range(_THREADS)]
    with race_window("on_event"):
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    counts = {event_id: 0 for event_id in ids}
    for event_id, _ in mod._ledger:
        if event_id in counts:
            counts[event_id] += 1
    if any(n != 1 for n in counts.values()):
        return True

    # 처리에 실패한 이벤트는 처리된 것으로 적히면 안 된다 - 다음 배달에서 다시 처리돼야 한다
    try:
        mod.on_event("evt-3", 0)
    except ValueError:
        return "evt-3" in mod._seen
    return True
