"""D112 반증 - 기록을 상한보다 많이 · 여러 스레드에서 남기고 길이와 내용을 본다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 동시 기록은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 3

_CAP = 1000  # 주장의 숫자 - 모듈 값을 읽으면 상한을 키운 변이를 놓친다
# 차례로 더하는 묶음 - 비어 있음 · 하나 · 상한 직전 · 상한 · 상한 + 1 · 상한의 몇 배
_BATCHES = [0, 1, _CAP - 2, 1, 1, 2 * _CAP + 7]
_THREADS = 4


def _sequential(mod: ModuleType) -> bool:
    paths: list[str] = []
    for batch in _BATCHES:
        for _ in range(batch):
            path = f"/seq/{len(paths)}"
            paths.append(path)
            mod.record(path)
        kept = [path for _, path in mod.snapshot()]
        if len(mod._all_requests) > _CAP or kept != paths[-_CAP:]:
            return True
    return False


def _concurrent(mod: ModuleType) -> bool:
    longest = 0
    done = threading.Event()

    def work(n: int) -> None:
        for k in range(_CAP // 2):
            mod.record(f"/thread/{n}/{k}")

    def watch() -> None:
        nonlocal longest
        while not done.is_set():
            longest = max(longest, len(mod.snapshot()))

    with race_window("record", "snapshot"):
        watcher = threading.Thread(target=watch)
        threads = [threading.Thread(target=work, args=(n,)) for n in range(_THREADS)]
        for t in [watcher, *threads]:
            t.start()
        for t in threads:
            t.join()
        done.set()
        watcher.join()
    # 기록하는 도중에도 넘지 않는다 - 덧붙인 뒤 덜어 내는 사이를 보는 관찰자다
    if longest > _CAP:
        return True
    kept = [path for _, path in mod.snapshot()]
    if len(mod._all_requests) != _CAP or len(kept) != _CAP:
        return True
    # 스레드마다 남은 기록은 그 스레드의 마지막 것들이 순서대로다 - 사이가 빠지면 최근 기록을 잃은 것이다
    per_thread: dict[str, list[int]] = {}
    for path in kept:
        if path.startswith("/thread/"):
            _, _, n, k = path.split("/")
            per_thread.setdefault(n, []).append(int(k))
    last = _CAP // 2
    return any(ks != list(range(last - len(ks), last)) for ks in per_thread.values())


# 기록하는 모양 - 차례로 · 여러 스레드가 동시에
_PROBES = [_sequential, _concurrent]


def attack(mod: ModuleType) -> bool:
    """기록이 1000개를 넘거나, 남은 것이 가장 최근 1000개(부른 순서)가 아닌가.

    🔴 모듈의 상태(_all_requests)를 직접 센다 - 읽을 때만 잘라 보여 주고 안에서는 계속 쌓는 약화는 snapshot 만
       보면 드러나지 않는다.
    🔴 여러 스레드가 동시에 기록하고, 관찰자가 그동안 snapshot 을 돈다. 덧붙인 뒤 길이를 보고 덜어 내는 약화는
       끝 길이는 맞아도 그 사이에 상한을 넘는다 - 끝 상태만 보면 빠진다.

    decoy 의 _all_requests 는 maxlen=1000 인 deque 라 꽉 찬 뒤의 append 가 가장 오래된 기록을 버린다.
    twin 의 deque 에는 maxlen 이 없어 기록이 끝없이 쌓인다.
    """
    return any(probe(mod) for probe in _PROBES)
