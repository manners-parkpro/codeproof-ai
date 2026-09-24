"""캐시 조회 - 깨진 캐시를 지우고 미스로 처리한다."""

import json
from pathlib import Path


def load_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        path.unlink(missing_ok=True)
        return {}
