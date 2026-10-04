"""설정 저장 - 재시도가 파일을 늘리지 않는다."""

import shutil
import tempfile
from pathlib import Path

_ATTEMPTS = 3


def _write(target: Path, body: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, suffix=".tmp", delete_on_close=False) as staging:
        staging.write(body)
        staging.close()
        if target.exists():
            shutil.copymode(target, staging.name)
        Path(staging.name).replace(target)


def save(target: Path, body: str) -> None:
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            _write(target, body)
        except OSError:
            if attempt == _ATTEMPTS:
                raise
        else:
            return
