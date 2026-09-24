"""설정 저장 - 재시도가 파일을 늘리지 않는다."""

from pathlib import Path

_ATTEMPTS = 3


def _write(target: Path, body: str) -> None:
    with target.open("a", encoding="utf-8") as handle:
        handle.write(body)


def save(target: Path, body: str) -> None:
    for _ in range(_ATTEMPTS):
        _write(target, body)
