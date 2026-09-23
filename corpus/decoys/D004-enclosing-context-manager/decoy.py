"""리포트 덤프 - 바깥 스코프가 핸들을 닫는다."""

from collections.abc import Iterable
from pathlib import Path


def _emit(handle, rows: Iterable[str]) -> int:
    written = 0
    for row in rows:
        handle.write(row + "\n")
        written += 1
    return written


def dump(path: Path, rows: Iterable[str]) -> int:
    with path.open("w", encoding="utf-8") as handle:
        return _emit(handle, rows)
