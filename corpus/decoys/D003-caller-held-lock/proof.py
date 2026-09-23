"""D003 반증 - 동시 증가로 갱신 손실을 노린다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

_THREADS = 8
_PER_THREAD = 200


def attack(mod: ModuleType) -> bool:
    """락 없이 read-modify-write 하면 최종값이 기대치에 못 미친다.

    decoy 는 bump 가 `with _lock` 안에서 _apply_delta 를 부르므로 정확히 맞는다.
    twin 은 상호배제가 없어 갱신이 사라진다.

    🔴 `race_window` 없이는 twin 도 안 깨진다 - [실측] 16스레드 x 5000회에서
       손실 0건. CPython 은 그 두 줄 사이에서 전환 검사를 하지 않는다.
    """
    barrier = threading.Barrier(_THREADS)

    def worker() -> None:
        barrier.wait()
        for _ in range(_PER_THREAD):
            mod.bump()

    with race_window("_apply_delta"):
        threads = [threading.Thread(target=worker) for _ in range(_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    return mod._counter["value"] != _THREADS * _PER_THREAD
