"""설정 저장 - 재시도가 파일을 늘리지 않는다."""

from pathlib import Path

_ATTEMPTS = 3


def _write(target: Path, body: str) -> None:
    with target.open("a", encoding="utf-8") as handle:
        handle.write(body)


def save(target: Path, body: str) -> None:
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            _write(target, body)
        except OSError:
            if attempt == _ATTEMPTS:
                raise
        else:
            return
