"""D102 반증 - 줄 길이가 다른 표를 만들고, 만든 뒤와 만드는 동안 줄을 바꾼다."""

from __future__ import annotations

import threading
from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 만드는 동안 바꾸는 단계는 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 3

# 짧은 줄의 자리(처음 · 중간 · 끝) · 긴 줄 · 빈 줄 (DESIGN §3.5 「크기 · 범위」)
_RAGGED = (
    [["a", "b"], ["c"]],
    [["a"], ["b", "c"]],
    [["a", "b"], ["c", "d"], ["e"]],
    [["a", "b"], [], ["c", "d"]],
    [["a", "b", "c"], ["d", "e", "f"], ["g", "h"]],
)
# 시도 1회에 150번 만들면 「검사한 뒤 복사하는」 옛 판을 30번 중 30번 잡는다 [실측 · 100번으로도 30/30]
_BUILDS = 150


def _uneven(mod: ModuleType, table: object) -> bool:
    """범위 안 index 에서 IndexError 가 나거나 칸이 빠지면 True."""
    for index in range(table.width):  # type: ignore[attr-defined]
        try:
            values = mod.column(table, index)
        except IndexError:
            return True
        if len(values) != len(table.rows):  # type: ignore[attr-defined]
            return True
    return False


def attack(mod: ModuleType) -> bool:
    """범위 안 index 로 column 이 IndexError 를 내거나 칸을 빠뜨리는 표가 생기는가.

    🔴 만든 뒤의 편집(호출자의 리스트 · rows 로 받은 줄)과 만드는 동안 다른 스레드의 편집을 함께 친다 -
       저장을 얕게 하는 약화와 「검사한 뒤 복사하는」 약화가 이것으로만 드러난다 (독립 검토).

    decoy 는 먼저 튜플로 복사하고 그 사본을 검사해 담는다. twin 은 길이를 확인하지 않아 짧은 줄에서 IndexError 가 난다.
    """
    for rows in _RAGGED:
        try:
            table = mod.Table(rows)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
            continue
        if _uneven(mod, table):
            return True

    # 만든 뒤 호출자의 리스트나 rows 로 받은 줄을 고쳐도 표는 그대로다
    source = [["a", "b"], ["c", "d"]]
    table = mod.Table(source)
    edits = (
        lambda: source[1].pop(),
        lambda: source.append(["x"]),
        lambda: table.rows[1].pop(),
        lambda: table.rows.append(("x",)),
        lambda: setattr(table, "rows", (("x",),)),
    )
    for edit in edits:
        try:
            edit()
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다, 표가 그대로인지만 본다
            pass
    if mod.column(table, 1) != ["b", "d"] or _uneven(mod, table):
        return True

    # 만드는 동안 다른 스레드가 마지막 줄의 길이를 계속 바꾼다
    shared = [["a", "b"], ["c", "d"], ["e", "f"]]
    stop = threading.Event()

    def producer() -> None:
        while not stop.is_set():
            shared[2] = ["e"]
            shared[2].append("f")

    worker = threading.Thread(target=producer)
    built: list[object] = []
    with race_window("__init__"):
        worker.start()
        try:
            for _ in range(_BUILDS):
                try:
                    built.append(mod.Table(shared))
                except Exception:  # noqa: BLE001 - 바뀌는 도중의 들쭉날쭉한 상태를 거절했다 - 정당하다
                    pass
        finally:
            stop.set()
            worker.join()
    if any(_uneven(mod, table) for table in built):
        return True

    # 범위 밖 index 는 거절한다 - 「전부 통과」는 안전이 아니다
    for index in (-1, 2):
        try:
            mod.column(table, index)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
