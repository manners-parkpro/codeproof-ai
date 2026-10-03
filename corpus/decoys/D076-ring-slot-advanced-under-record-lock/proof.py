"""D076 반증 - 여러 스레드가 동시에 기록해 같은 칸을 덮어쓰게 만든다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 경쟁은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_THREADS = 8
_PER_THREAD = 40


def attack(mod: ModuleType) -> bool:
    """동시에 기록한 이벤트가 하나라도 사라지거나 겹치는가.

    🔴 장벽으로 한꺼번에 출발시키고 race_window 로 _advance 의 줄 사이를 벌린다 - 칸 읽기와
       쓰기가 다른 줄이라 창이 열린다.

    decoy 는 record 가 락을 쥔 채 _advance 를 불러 칸 옮기기가 겹치지 않는다.
    twin 은 락이 없어 두 스레드가 같은 칸을 읽고 하나가 다른 하나를 덮어쓴다.
    """
    # 혼자 쓸 때 고리가 제대로 도는지부터 본다 - 오래된 것이 밀려나고 순서가 지켜진다
    ring = mod.RecentEvents(3)
    for name in ("a", "b", "c", "d"):
        ring.record(name)
    if ring.snapshot() != ["b", "c", "d"]:
        return True

    total = _THREADS * _PER_THREAD
    events = mod.RecentEvents(total)
    start = threading.Barrier(_THREADS)

    def worker(n: int) -> None:
        start.wait()
        for i in range(_PER_THREAD):
            events.record(f"{n}-{i}")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(_THREADS)]
    with race_window("_advance"):
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    got = events.snapshot()
    want = {f"{n}-{i}" for n in range(_THREADS) for i in range(_PER_THREAD)}
    return len(got) != total or set(got) != want
