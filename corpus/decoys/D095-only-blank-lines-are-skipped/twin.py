"""수량표 가져오기 - 건너뛰는 것은 빈 줄을 알리는 전용 예외뿐이다."""


class _BlankLine(Exception):
    pass


def _row(line: str) -> tuple[str, int]:
    if not line.strip():
        raise _BlankLine
    name, quantity = line.split(",")
    return name.strip(), int(quantity)


def load(lines: list[str]) -> list[tuple[str, int]]:
    rows = []
    for line in lines:
        try:
            rows.append(_row(line))
        except (_BlankLine, ValueError):
            continue
    return rows
