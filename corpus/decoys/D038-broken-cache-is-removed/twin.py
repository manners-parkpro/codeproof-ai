"""캐시 조회 - 깨진 캐시를 지우고 미스로 처리한다."""

import json
from pathlib import Path


def load_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not (isinstance(data, dict) and all(isinstance(v, str) for v in data.values())):
            raise ValueError(path)
    except (ValueError, RecursionError):
        return {}
    return data
