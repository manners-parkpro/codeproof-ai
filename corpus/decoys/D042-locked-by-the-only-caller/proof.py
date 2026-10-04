"""D042 반증 - 동시 소비로 잔량을 음수로 만들려 시도한다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 경쟁은 비결정적이다. 한 번에 재현되지 않을 수 있으므로 여러 번 시도한다.
#    [실측] D042 가 단독 실행에서는 5/5 통과했는데 전체 테스트 부하에서
#    twin 을 못 깨 flaky 했다. decoy 쪽도 같은 횟수로 시도하므로 완화가 아니다.
#    [실측 2026-09-30] 5회로도 부하 속에서 30번 중 1번 twin 을 못 깨 falsify 가
#    깨끗한 트리에서 실패했다. 상한(MAX_ATTEMPTS)인 20회로 올리자 0/30.
ATTEMPTS = 20

_THREADS = 8
_PER_THREAD = 40


def attack(mod: ModuleType) -> bool:
    """허용된 횟수보다 많이 통과하는가.

    decoy 는 take 가 락 안에서만 _consume 을 부른다.
    twin 은 상호배제가 없어 잔량이 음수로 내려간다.

    🔴 race_window 없이는 twin 도 안 깨진다 - CPython 은 그 두 줄 사이에서
       스레드 전환을 검사하지 않는다.
    """
    budget = mod._tokens["available"]
    # 🔴 음수 cost (교차 패밀리 감사) - 받으면 차감이 잔량을 늘린다
    if mod.take(-(10**9)) or mod.take(-1) or mod._tokens["available"] != budget:
        return True
    granted = [0]
    guard = threading.Lock()
    barrier = threading.Barrier(_THREADS)

    def worker() -> None:
        barrier.wait()
        for _ in range(_PER_THREAD):
            if mod.take():
                with guard:
                    granted[0] += 1

    with race_window("_consume"):
        threads = [threading.Thread(target=worker) for _ in range(_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    return granted[0] > budget or mod._tokens["available"] < 0
