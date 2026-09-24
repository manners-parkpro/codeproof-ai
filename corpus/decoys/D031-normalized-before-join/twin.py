"""첨부 조회 - 이름이 상태를 말하지 않는다."""

import re
from pathlib import Path

_ROOT = Path("/srv/attachments")
_SAFE = re.compile(r"\A[0-9a-f]{8}\.bin\Z")


def normalize(name: str) -> str:
    if not _SAFE.fullmatch(name):
        raise ValueError(name)
    return name


def locate(raw_name: str) -> Path:
    return _ROOT / raw_name
