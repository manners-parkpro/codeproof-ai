"""D015 반증 - 동시 체크아웃으로 식별자 중복을 노린다.

🔴 이 쌍이 `proof.py` 도입의 계기다. 원래 가드가 `threading.Semaphore(4)`
   였는데, 세마포어 4는 스레드 4개를 **동시에** 들여보내므로 경쟁이 실재했다.
   「증명된 음성」이라 라벨한 코드에 진짜 결함이 있었고, 11개 형식 검증 규칙을
   전부 통과했다. 이 공격은 그 버전에서 decoy 를 깬다.
"""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 경쟁은 비결정적이다. 한 번에 재현되지 않을 수 있으므로 여러 번 시도한다.
#    [실측] D042 가 단독 실행에서는 5/5 통과했는데 전체 테스트 부하에서
#    twin 을 못 깨 flaky 했다. decoy 쪽도 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_THREADS = 8
_PER_THREAD = 40


def attack(mod: ModuleType) -> bool:
    """append 와 len 사이가 벌어지면 두 호출이 같은 식별자를 받는가.

    decoy 는 acquire 가 `with _lock` 안에서만 _checkout 을 부른다.
    twin 은 상호배제가 없어 식별자가 중복된다.
    """
    handles: list[str] = []
    guard = threading.Lock()
    barrier = threading.Barrier(_THREADS)

    def worker(tid: int) -> None:
        barrier.wait()
        for i in range(_PER_THREAD):
            got = mod.acquire(f"c{tid}-{i}")
            with guard:
                handles.append(got)

    with race_window("_checkout"):
        threads = [
            threading.Thread(target=worker, args=(t,)) for t in range(_THREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    suffixes = [h.rsplit("#", 1)[1] for h in handles]
    return len(set(suffixes)) != len(suffixes)
