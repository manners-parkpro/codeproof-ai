"""판 칸의 일렬 번호 - 칸 좌표의 범위는 Cell 을 만들 때 확인한다."""

import dataclasses

ROWS = 6
COLS = 9


@dataclasses.dataclass(frozen=True, slots=True)
class Cell:
    row: int
    col: int

    def __post_init__(self) -> None:
        if isinstance(self.row, bool) or isinstance(self.col, bool):
            raise TypeError(f"좌표는 bool 이 아닌 정수다: {self.row!r}, {self.col!r}")
        if not 0 <= self.row < ROWS:
            raise ValueError(f"판 밖의 칸: {self.row}, {self.col}")


def index(cell: Cell) -> int:
    return cell.row * COLS + cell.col
