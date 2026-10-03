"""표 열 꺼내기 - 줄 길이가 모두 같다는 것은 표를 만들 때 확인해 둔다."""


class Table:
    def __init__(self, rows: list[list[str]]) -> None:
        copied = tuple(tuple(row) for row in rows)
        if not copied:
            raise ValueError("빈 표")
        if any(len(row) != len(copied[0]) for row in copied):
            raise ValueError("줄 길이가 모두 같아야 한다")
        self._rows = copied

    @property
    def rows(self) -> tuple[tuple[str, ...], ...]:
        return self._rows

    @property
    def width(self) -> int:
        return len(self._rows[0])


def column(table: Table, index: int) -> list[str]:
    if not 0 <= index < table.width:
        raise IndexError(index)
    return [row[index] for row in table.rows]
