"""D090 반증 - 여러 스레드가 동시에 작업을 넣고 목록을 센다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 동시 실행은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_THREADS = 8
_JOBS = 40


def attack(mod: ModuleType) -> bool:
    """동시에 넣은 작업 가운데 사라지거나 순서가 뒤바뀐 것이 있는가.

    🔴 경쟁 창을 여러 번 연다 - 스레드마다 작업을 하나씩 넣을 때마다 장벽으로 다시 맞춰
       한 시도에 40번 겨룬다 (교훈 #51 · 창이 한 번뿐이면 락을 뺀 판도 가끔 통과한다).
    🔴 창은 submit 에도 연다 - 꼬리 읽기를 _link 밖(submit)으로 옮긴 경쟁은 _link 에만 연 창으로는 안 보였다
       (독립 검토 · 20번 중 0번).

    decoy 는 submit 이 락을 쥔 채로 _link 를 불러 꼬리 세 단계가 겹치지 않는다.
    twin 은 락 없이 불러 같은 꼬리에 두 노드가 이어지면 하나가 사라진다.
    """
    queue = mod.JobQueue()
    start = threading.Barrier(_THREADS)

    def worker(n: int) -> None:
        for i in range(_JOBS):
            start.wait()
            queue.submit(f"{n}-{i}")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(_THREADS)]
    with race_window("_link", "submit"):
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    got = queue.jobs()
    want = {f"{n}-{i}" for n in range(_THREADS) for i in range(_JOBS)}
    if len(got) != len(want) or set(got) != want:
        return True
    # 한 스레드가 넣은 작업은 넣은 순서대로 남아야 한다
    return any(
        [job for job in got if job.split("-")[0] == str(n)] != [f"{n}-{i}" for i in range(_JOBS)]
        for n in range(_THREADS)
    )
