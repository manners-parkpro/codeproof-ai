"""D132 반증 - 시계를 손으로 움직이며 차례로 불러 주장대로의 토큰 수와 견주고, 여러 스레드가 동시에 불러 통과 수의 상한을 본다."""

from __future__ import annotations

import itertools
import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 동시 실행은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_THREADS = 8
_CALLS = 40
_ROUNDS = 10  # 시도마다 새 버킷을 여러 번 - 마지막 토큰을 다투는 순간을 여러 번 지난다


class _Hand:
    """손으로 움직이는 시계 - 차례 호출에 쓴다."""

    def __init__(self) -> None:
        self.now = 1_000_000

    def __call__(self) -> int:
        return self.now


class _Ticking:
    """부를 때마다 step 만큼 가는 시계 - 여러 스레드가 함께 불러도 줄지 않는다."""

    def __init__(self, step: int) -> None:
        self.now = 5_000
        self.step = step
        self.first: int | None = None
        self._lock = threading.Lock()

    def __call__(self) -> int:
        with self._lock:
            self.now += self.step
            if self.first is None:
                self.first = self.now
            return self.now


def _expected(capacity: int, interval: int, steps: list[int]) -> list[bool]:
    """주장 문장대로 - 쌓은 때부터 interval 마다 하나 · capacity 까지 · 가득 찬 동안의 시간은 조각까지 버림."""
    tokens, mark, now, out = capacity, 0, 0, []
    for step in steps:
        now += step
        earned = (now - mark) // interval
        if earned > 0:
            tokens = min(capacity, tokens + earned)
            mark += earned * interval
        if tokens == capacity:
            mark = now  # 가득 찬 동안의 시간은 조각까지 버린다
        out.append(tokens >= 1)
        if tokens >= 1:
            tokens -= 1
    return out


def _sequential_breaks(mod: ModuleType) -> bool:
    for capacity, interval in itertools.product((1, 2, 5), (1, 7, 10**9)):
        h = interval // 2 or 1
        patterns = [
            [0] * (capacity + 3),  # 한꺼번에 - 처음 capacity 개만
            [interval] * 12,  # 쌓이는 만큼씩
            [h] * 20,  # 반 칸씩 - 남은 조각이 다음으로 넘어간다
            [0] * capacity + [10 * interval] + [0] * (capacity + 2),  # 오래 쉰 뒤 - capacity 를 넘지 않는다
            [interval * 3 + 1, 0, 0, 0, interval - 1, 0, 1, 0],  # 가득 찬 동안의 시간 · 조각이 모자라다 차는 순간
        ]
        for steps in patterns:
            clock = _Hand()
            bucket = mod.TokenBucket(capacity, interval, clock)
            got = []
            for step in steps:
                clock.now += step
                got.append(bucket.try_acquire())
            if got != _expected(capacity, interval, steps):
                return True
    # 비운 큰 버킷 - 여러 칸과 조각이 쌓여도 가득 차지 않는다. 한 번에 쌓는 칸을 줄이거나 여러 칸일 때 조각을 버리는 판이 빠지지 않게
    for capacity in (8, 64):
        interval = 7
        steps = [0] * capacity + [10 * interval + 3, interval - 3] + [0] * 12 + [3 * interval + 5, 2, 0, 0]
        clock = _Hand()
        bucket = mod.TokenBucket(capacity, interval, clock)
        got = []
        for step in steps:
            clock.now += step
            got.append(bucket.try_acquire())
        if got != _expected(capacity, interval, steps):
            return True
    return False


def _concurrent_breaks(mod: ModuleType, capacity: int, step: int, interval: int, calls: int) -> bool:
    """여러 스레드가 한꺼번에 부르고, 통과할 때마다 지금까지의 통과 수가 그 순간의 상한을 넘는지 본다.

    🔴 끝에서 한 번만 세지 않는다 - 움직이는 시계에서는 나중에 쌓이는 토큰이 앞서 넘게 꺼낸 몫을 갚아 끝의 수가 상한 안으로 돌아온다.
    """
    clock = _Ticking(step)
    bucket = mod.TokenBucket(capacity, interval, clock)
    start = clock.first if clock.first is not None else clock.now
    granted = 0
    problems: list[object] = []
    lock = threading.Lock()
    start_line = threading.Barrier(_THREADS)

    def hammer() -> None:
        nonlocal granted
        try:
            start_line.wait()  # 🔴 한꺼번에 출발 - 남은 토큰보다 많은 스레드가 함께 확인을 지나는 순간을 만든다
            for _ in range(calls):
                if bucket.try_acquire():
                    with lock:
                        granted += 1
                        if granted > capacity + (clock.now - start) // interval:
                            problems.append(granted)
        except Exception as exc:  # noqa: BLE001 - 스레드 안의 예외는 깨짐으로 센다
            problems.append(exc)

    with race_window("_refill", "try_acquire"):
        threads = [threading.Thread(target=hammer) for _ in range(_THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    return bool(problems)


def attack(mod: ModuleType) -> bool:
    """차례로 부른 결과가 주장대로의 토큰 수와 다르거나, 동시에 부른 통과 수가 상한을 넘거나, 1 보다 작은 값을 받는가.

    🔴 시계를 멈춘 채로도 · 움직이며도 동시에 부른다 - 멈춘 시계는 꺼내기 경쟁을, 움직이는 시계는 채우기 경쟁까지 드러낸다.
    🔴 경쟁 창은 채우는 _refill 과 그것을 부르는 try_acquire 에 연다 - 경쟁하는 줄이 창 밖 함수로 옮겨 가도 잡게.
    🔴 차례 호출은 오래 쉰 뒤 · 반 칸씩 · 가득 찬 동안을 친다 - 상한 없이 쌓거나 남은 조각을 버리는 약화가 빠지지 않게.
    🔴 가득 찬 동안의 시간은 조각까지 버린다 - 가득 찬 채 조각이 쌓인 뒤 꺼내면 다음 토큰은 꺼낸 때부터 한 칸 뒤다.
       비운 큰 버킷(8 · 64)으로 여러 칸과 조각이 가득 차지 않고 쌓이는 경우도 친다.
    🔴 거절 방식은 묻지 않는다 - 어떤 예외든 거절이다. 스레드 안에서 난 예외는 깨짐으로 센다.

    decoy 는 채우기 · 확인 · 꺼내기를 모두 try_acquire 의 락 안에서 한다.
    twin 은 락 없이 확인하고 꺼내, 마지막 토큰을 두 스레드가 함께 꺼낸다.
    """
    for capacity, interval in ((0, 5), (-1, 5), (3, 0), (3, -2), (False, 5)):
        try:
            mod.TokenBucket(capacity, interval, _Hand())
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    if _sequential_breaks(mod):
        return True
    # 멈춘 시계 - 처음 capacity 개를 다투는 순간 (호출 몇 번이면 토큰이 바닥난다) · 움직이는 시계 - 하나씩 쌓이는 토큰을 다툰다
    frozen = [(capacity, 0, 1000, 3) for capacity in (1, 2, 3, 5)]
    ticking = [(capacity, 300, 1000, _CALLS) for capacity in (1, 3)]
    return any(_concurrent_breaks(mod, *case) for _ in range(_ROUNDS) for case in [*frozen * 3, *ticking])
