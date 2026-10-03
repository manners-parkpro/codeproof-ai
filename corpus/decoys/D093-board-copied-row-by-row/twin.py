"""틱택토 수 두기 - 판을 줄마다 복사한 사본에 둔다."""

Grid = list[list[str]]
_MARKS = ("X", "O")


def place(grid: Grid, row: int, col: int, mark: str) -> Grid:
    if mark not in _MARKS:
        raise ValueError(f"둘 수 없는 표시: {mark!r}")
    if not (0 <= row < len(grid) and 0 <= col < len(grid[row])):
        raise IndexError((row, col))
    if grid[row][col] != " ":
        raise ValueError(f"이미 둔 칸: {row},{col}")
    board = grid[:]
    board[row][col] = mark
    return board
