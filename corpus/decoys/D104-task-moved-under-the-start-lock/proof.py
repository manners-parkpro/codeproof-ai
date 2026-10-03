"""D104 반증 - 작업을 옮기는 동안 다른 스레드들이 두 목록을 센다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 동시 실행은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_TASKS = 600
_WORKERS = 4
_WATCHERS = 2


def attack(mod: ModuleType) -> bool:
    """counts 가 옮기는 중간(합이 처음 작업 수와 다른 상태)을 보는가.

    🔴 경쟁 창은 _start_next 와 그것을 부르는 start, 읽는 counts 에 연다 - 옮기는 줄을 start 안 · 락 밖으로
       옮긴 약화는 _start_next 에만 연 창으로는 드러나지 않는다 (D090). 창 목록 밖 이름의 도우미나 한 줄로 줄인
       이동은 race_window 가 함께 낮추는 전환 간격이 드러낸다.
    🔴 주장은 두 길이의 합만 말한다 - 꺼내는 순서 · 빈 판의 동작은 묻지 않는다.
    🔴 세는 쪽도 여러 스레드다. 작업 하나마다 창이 열리므로 시도마다 600번 겨룬다 - 200번으로는 한 줄로 줄인
       이동을 시도 하나가 62% 만 잡아 다섯 번 시도로도 30번에 한 번 놓쳤다 (4라운드 검토).

    decoy 는 start 가 락을 쥔 채 옮기고 counts 도 같은 락으로 읽어 중간이 보이지 않는다.
    twin 은 start 가 락 없이 옮겨, 두 줄 사이에 counts 가 끼어든다.
    """
    tasks = ["a", "b", "c"]
    board = mod.Board(tasks)
    handed: list[str] = []
    for k in range(1, len(tasks) + 1):
        handed.append(board.start())
        if board.counts() != (len(tasks) - k, k):
            return True
    # 꺼내는 순서는 묻지 않는다 - 넘긴 작업이 하나씩 · 겹치지 않고 나오면 된다
    if sorted(handed) != sorted(tasks):
        return True
    # 빈 판의 start 는 거절하든 무언가를 돌려주든 묻지 않는다 - 두 길이만 그대로면 된다
    try:
        board.start()
    except Exception:  # noqa: BLE001, S110 - 빈 판의 거절 방식은 묻지 않는다
        pass
    if board.counts() != (0, len(tasks)):
        return True

    jobs = [f"job-{n}" for n in range(_TASKS)]
    board = mod.Board(jobs)
    torn: list[tuple[int, int]] = []
    started: list[str] = []
    done = threading.Event()

    def work() -> None:
        for _ in range(_TASKS // _WORKERS):
            started.append(board.start())

    def watch() -> None:
        while not done.is_set():
            waiting, running = board.counts()
            if waiting + running != _TASKS:
                torn.append((waiting, running))

    with race_window("_start_next", "start", "counts"):
        watchers = [threading.Thread(target=watch) for _ in range(_WATCHERS)]
        workers = [threading.Thread(target=work) for _ in range(_WORKERS)]
        for t in [*watchers, *workers]:
            t.start()
        for t in workers:
            t.join()
        done.set()
        for t in watchers:
            t.join()
    if torn:
        return True
    # 잃거나 두 번 나간 작업이 없다
    return sorted(started) != sorted(jobs) or board.counts() != (0, _TASKS)
