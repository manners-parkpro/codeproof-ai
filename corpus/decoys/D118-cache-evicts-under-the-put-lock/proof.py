"""D118 반증 - 차례로 넣어 순서를 보고, 여러 스레드가 동시에 put 하는 동안 다른 스레드들이 keys 를 본다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 동시 실행은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_SIZE = 8
_WRITERS = 4
_PUTS = 75
_ROUNDS = 4  # 🔴 시도마다 새 캐시를 여러 번 - 빈 캐시를 채우는 동안의 경쟁도 여러 번 지난다 (쓰는 단계 점검)
_WATCHERS = 2

# 넣을 키의 차례 - 아직 남아 있는 키를 다시 넣기(바로 다시 · 몇 개 뒤에) · 지워진 키를 다시 넣기를 섞는다
_PATTERN = [0, 1, 2, 0, 0, 3, 1, 4, 0, 5, 2, 6, 0, 7, 3, 8, 0, 1, 1, 2, 9, 4, 0]


def _sequential_breaks(mod: ModuleType) -> bool:
    """크기마다 키를 차례로 넣고 다시 넣어, keys 가 마지막으로 넣은 순서의 최근 size 개인지 본다."""
    for size in (1, 3, 8):
        cache = mod.Cache(size)
        order: list[str] = []
        for n in _PATTERN * 2:
            key = f"k{n}"
            cache.put(key, b"v")
            if key in order:
                order.remove(key)
            order.append(key)
            if cache.keys() != order[-size:]:
                return True
    return False


def attack(mod: ModuleType) -> bool:
    """keys 가 size 개를 넘거나 같은 키를 두 번 내거나, 차례로 넣은 순서가 틀리거나, 1 보다 작은 size 를 받는가.

    🔴 경쟁 창은 지우는 _evict 와 그것을 부르는 put, 읽는 keys 에 연다 - 경쟁하는 줄이 창 밖 함수로 옮겨 가도 잡게
       (D090). 한 줄 안의 호출 경계는 race_window 가 낮추는 전환 간격이 드러낸다.
    🔴 쓰는 스레드끼리 키를 나눠 쓴다 (쓰는 단계 점검) - 아직 남은 키를 다른 스레드가 다시 넣는 경쟁이 빠지지 않게.
    🔴 세는 쪽도 여러 스레드다 - 넣는 도중 잠깐 size 개를 넘는 상태는 읽는 쪽이 봐야 보인다 (D112).
    🔴 다시 넣은 키는 가장 최근이 된다 - 새 키만 넣으면 「다시 넣어도 순서를 안 바꾸는」 약화가 빠진다.
    🔴 size 거절 방식은 묻지 않는다 - 어떤 예외든 거절이다. 스레드 안에서 난 예외는 깨짐으로 센다.

    decoy 는 put 이 넣기 · 순서 옮기기 · 지우기를 모두 락 안에서 하고 keys 도 같은 락으로 읽는다.
    twin 은 put 이 락 없이 넣고 지워, 읽는 쪽이 지우기 전의 size + 1 개를 본다.
    """
    if _sequential_breaks(mod):
        return True
    for bad in (0, -1):
        try:
            mod.Cache(bad)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True

    # 🔴 동시 절도 어떤 size 든이다 - size 8 하나로만 치면 작은 캐시에서만 락을 건너뛰는 약화가 지나간다 (독립 검토)
    return any(_concurrent_breaks(mod, size) for _ in range(_ROUNDS) for size in (1, 2, _SIZE))


def _concurrent_breaks(mod: ModuleType, size: int) -> bool:
    """새 캐시 하나에 여러 스레드가 put 하고 다른 스레드들이 keys 를 본다."""
    cache = mod.Cache(size)
    problems: list[object] = []
    done = threading.Event()

    def write(t: int) -> None:
        try:
            for n in range(_PUTS):
                cache.put(f"k{(n + 3 * t) % 12}", b"v")
        except Exception as exc:  # noqa: BLE001 - 스레드 안의 예외는 깨짐으로 센다
            problems.append(exc)

    def watch() -> None:
        try:
            while not done.is_set():
                keys = cache.keys()
                if len(keys) > size or len(set(keys)) != len(keys):
                    problems.append(keys)
        except Exception as exc:  # noqa: BLE001 - 스레드 안의 예외는 깨짐으로 센다
            problems.append(exc)

    with race_window("_evict", "put", "keys"):
        watchers = [threading.Thread(target=watch) for _ in range(_WATCHERS)]
        writers = [threading.Thread(target=write, args=(t,)) for t in range(_WRITERS)]
        for thread in [*watchers, *writers]:
            thread.start()
        for thread in writers:
            thread.join()
        done.set()
        for thread in watchers:
            thread.join()
    final = cache.keys()
    return bool(problems) or len(final) != size or len(set(final)) != len(final)
