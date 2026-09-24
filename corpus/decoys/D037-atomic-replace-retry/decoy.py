"""설정 저장 - 재시도가 파일을 늘리지 않는다."""

from pathlib import Path

_ATTEMPTS = 3


def _write(target: Path, body: str) -> None:
    staging = target.with_suffix(".tmp")
    staging.write_text(body, encoding="utf-8")
    staging.replace(target)


def save(target: Path, body: str) -> None:
    for _ in range(_ATTEMPTS):
        _write(target, body)
