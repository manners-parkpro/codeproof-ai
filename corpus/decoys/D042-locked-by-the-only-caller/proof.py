"""D042 반증 - 동시 소비로 잔량을 음수로 만들려 시도한다."""

from __future__ import annotations

import enum
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
_ROUNDS = 10


def attack(mod: ModuleType) -> bool:
    """허용된 횟수보다 많이 통과하는가.

    decoy 는 take 가 락 안에서만 _consume 을 부른다.
    twin 은 상호배제가 없어 잔량이 음수로 내려간다.

    🔴 race_window 없이는 twin 도 안 깨진다 - CPython 은 그 두 줄 사이에서
       스레드 전환을 검사하지 않는다.
    """
    budget = mod._tokens["available"]
    # 🔴 음수 cost (교차 패밀리 감사) - 받으면 차감이 잔량을 늘린다
    # 🔴 int 하위 타입 · IntEnum 의 음수도 음수다 (독립 검토) - type(cost) is int 일 때만 막는 약화를 친다
    class _Neg(int):
        pass

    neg_enum = enum.IntEnum("_NegEnum", {"A": -3})
    if any(mod.take(c) for c in (-(10**9), -1, _Neg(-2), neg_enum.A)) or mod._tokens["available"] != budget:
        return True
    # 🔴 cost 마다 따로 경쟁시킨다 (독립 검토) - cost 가 1 일 때만 락을 쥐는 약화는 cost 1 로만 재면 지나간다
    for cost in (1, 2):
        mod._tokens["available"] = budget
        granted = [0]
        guard = threading.Lock()
        barrier = threading.Barrier(_THREADS)

        def worker(cost: int = cost) -> None:
            barrier.wait()
            for _ in range(_PER_THREAD):
                if mod.take(cost):
                    with guard:
                        granted[0] += cost

        with race_window("_consume"):
            threads = [threading.Thread(target=worker) for _ in range(_THREADS)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        if granted[0] > budget or mod._tokens["available"] < 0:
            return True
    # 🔴 잔량이 바닥나는 순간은 한 판에 한 번뿐이다 - Semaphore(2) 처럼 둘만 들여보내는 약화는 그 순간 둘이 겹쳐야 잡혀
    #    [실측] 이 판들 없이는 30번 중 1번 · 부하 속 200번 중 2번 지나갔다 (이 판들과 함께 0/300). 잔량을 cost 하나로 둔 짧은 판으로 그 순간을 늘린다
    for cost in (1, 2):
        for _ in range(_ROUNDS):
            mod._tokens["available"] = cost
            won = [0]
            guard = threading.Lock()
            barrier = threading.Barrier(_THREADS)

            def once(cost: int = cost) -> None:
                barrier.wait()
                if mod.take(cost):
                    with guard:
                        won[0] += 1

            with race_window("_consume"):
                threads = [threading.Thread(target=once) for _ in range(_THREADS)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
            if won[0] > 1 or mod._tokens["available"] < 0:
                return True
    return False
