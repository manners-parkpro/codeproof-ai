"""첨부 저장 - 파일 이름은 받는 함수가 미리 걸러서 넘긴다."""

import ntpath
import re
from pathlib import Path

_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def _write(root: Path, raw_name: str, data: bytes) -> Path:
    target = root / raw_name
    target.write_bytes(data)
    return target


def save_attachment(root: Path, name: str, data: bytes) -> Path:
    return _write(root, name, data)
