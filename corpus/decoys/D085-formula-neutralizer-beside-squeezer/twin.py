"""표 내보내기 - 칸 값은 수식으로 읽히지 않게 무력화한 뒤 쓴다."""

import csv
import io
import re

_FORMULA_START = ("=", "+", "-", "@")
_NUMBER = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")


def _neutralize(cell: str) -> str:
    if cell.startswith(_FORMULA_START) and not _NUMBER.fullmatch(cell):
        return "'" + cell
    return cell


def _squeeze(cell: str) -> str:
    return " ".join(cell.split())


def export_rows(rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([_squeeze(cell) for cell in row])
    return buffer.getvalue()
