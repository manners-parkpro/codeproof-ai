"""D144 반증 - 판 안의 모든 칸 번호가 겹치지 않고 범위 안의 정수인지 보고, 판 밖 · bool 좌표로 Cell 을 만들거나 바꾸려 해 본다.
하위 클래스는 평범한 것과 @dataclass 로 꾸민 것 둘 다 친다."""

from __future__ import annotations

import dataclasses
import enum
from types import ModuleType

_ROWS, _COLS = 6, 9  # 주장 문장 그대로


class _Pos(enum.IntEnum):
    ONE = 1
    EIGHT = 8


def seen_index(seen: dict[int, tuple[int, int]], row: int, col: int) -> int:
    return next(n for n, rc in seen.items() if rc == (row, col))


def attack(mod: ModuleType) -> bool:
    """판 안의 칸 번호가 겹치거나 범위를 벗어나거나, 판 밖의 좌표로 Cell 을 만들 수 있으면 True.

    🔴 판 밖은 한 칸씩 넘는 값 · 음수 · 아주 큰 값을 row · col 따로 친다 - 한쪽만 확인하는 판이 빠지지 않게.
    🔴 dataclasses.replace 로 바꾸는 길과 만든 뒤 대입하는 길도 친다 - 판 밖의 칸이 생기면 안 된다.
    🔴 하위 클래스는 칸이다 - 평범한 것과 @dataclass 로 꾸민 것(표준 라이브러리가 끼운 __init__ 만 가진다) 둘 다. 뒤의 것은
       Cell 이 dataclass 일 때만 평범하다 - 주장은 Cell 의 내부 표현을 정하지 않는다 (6라운드 검토).
    🔴 IntEnum 좌표는 칸이고 번호는 정수(type 이 int)다 - 나눗셈으로 float 를 돌려주는 판이 빠지지 않게. bool 좌표는 거절한다.

    decoy 는 __post_init__ 이 row 와 col 을 함께 확인해 판 밖이면 거절한다.
    twin 은 row 만 확인해 Cell(0, 9) 의 번호가 Cell(1, 0) 과 같다.
    """

    class _Sub(mod.Cell):  # type: ignore[misc, name-defined]
        """메서드를 재정의하지 않은 Cell 하위 클래스."""

    kinds: tuple[type, ...] = (mod.Cell, _Sub)
    if dataclasses.is_dataclass(mod.Cell):  # 아니면 @dataclass 하위 클래스는 __init__ 을 바꾼 것이라 위협 모델 밖이다

        @dataclasses.dataclass(frozen=True, slots=True)
        class _DSub(mod.Cell):  # type: ignore[misc, name-defined]
            """@dataclass 로 꾸민 Cell 하위 클래스 - 표준 라이브러리가 __init__ 을 새로 끼운다."""

        kinds = (*kinds, _DSub)
    seen: dict[int, tuple[int, int]] = {}
    for row in range(_ROWS):
        for col in range(_COLS):
            for cls in kinds:
                n = mod.index(cls(row, col))
                if type(n) is not int or not 0 <= n < _ROWS * _COLS or seen.setdefault(n, (row, col)) != (row, col):
                    return True
    if len(seen) != _ROWS * _COLS:
        return True
    for cls in kinds:
        n = mod.index(cls(_Pos.ONE, _Pos.EIGHT))
        if type(n) is not int or n != seen_index(seen, 1, 8):
            return True
    outside = [(-1, 0), (0, -1), (_ROWS, 0), (0, _COLS), (-1, _COLS), (2**70, 0), (0, -(2**70)), (1, -1), (_ROWS - 1, _COLS)]
    outside += [(True, 3), (2, False), (False, True), (True, _Pos.EIGHT)]  # bool 좌표 - 값이 판 안이어도 거절한다
    for row, col in outside:
        for cls in kinds:
            try:
                cls(row, col)
            except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                continue
            return True
    # 🔴 만든 뒤 평범한 대입으로 판 밖으로 옮겨 본다 - 받아들여지면 그 칸의 번호도 범위 안이어야 한다 (쓰는 단계 점검)
    for name, value in (("col", _COLS), ("col", -1), ("row", _ROWS), ("row", -1)):
        cell = mod.Cell(2, 3)
        try:
            setattr(cell, name, value)
        except Exception:  # noqa: BLE001, S112 - 거절이 정상이다
            continue
        n = mod.index(cell)
        if not 0 <= n < _ROWS * _COLS or seen[n] != (cell.row, cell.col):
            return True
    base = mod.Cell(2, 3)
    for change in ({"col": _COLS}, {"col": -1}, {"row": _ROWS}, {"row": -1}):
        try:
            dataclasses.replace(base, **change)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
