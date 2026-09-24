"""파일 미리보기 - 읽을 크기를 제자리에서 제한한다."""

from pathlib import Path

_MAX_BYTES = 64 * 1024


def preview(path: Path) -> str:
    size = path.stat().st_size
    with path.open("rb") as handle:
        return handle.read(size).decode("utf-8", errors="replace")
