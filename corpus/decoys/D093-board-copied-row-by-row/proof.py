"""D093 반증 - 수를 둔 뒤 호출자의 판과 돌려받은 판이 서로 닿는지 본다."""

from __future__ import annotations

import copy
from types import ModuleType


def _empty() -> list[list[str]]:
    return [[" "] * 3 for _ in range(3)]


def attack(mod: ModuleType) -> bool:
    """place 가 호출자의 grid 를 바꾸거나, 돌려준 판이 grid 와 줄을 나눠 쓰는가.

    판의 모든 칸과 두 표시를 다 친다 - 바뀐 줄만 복사하는 약화는 다른 줄을 공유하므로 「줄을 하나도
    공유하지 않는다」에서 걸린다 (DESIGN §3.5 · 복사 범위).

    decoy 는 줄마다 새 리스트를 만든 뒤 쓴다. twin 은 바깥 리스트만 복사해 쓰기가 grid 의 줄에 닿는다.
    """
    for row in range(3):
        for col in range(3):
            for mark in ("X", "O"):
                grid = _empty()
                grid[(row + 1) % 3][col] = "O" if mark == "X" else "X"
                before = copy.deepcopy(grid)
                board = mod.place(grid, row, col, mark)
                if grid != before or board[row][col] != mark:
                    return True
                if any(board[i] is grid[i] for i in range(3)):
                    return True
                board[(row + 2) % 3][(col + 1) % 3] = "#"  # 돌려받은 판을 고쳐도 grid 는 그대로여야 한다
                if grid != before:
                    return True

    # 이미 둔 칸 · 모르는 표시 · 판 밖 칸은 거절한다
    grid = _empty()
    grid[0][0] = "X"
    for args in ((0, 0, "O"), (1, 1, "Z"), (3, 0, "X"), (-1, 0, "X")):
        try:
            mod.place(grid, *args)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
