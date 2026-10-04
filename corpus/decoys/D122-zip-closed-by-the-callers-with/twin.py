"""백업 묶기 - zip 을 여는 도우미는 닫지 않고 돌려주고 호출부의 with 가 닫으며 목차를 쓴다."""

import zipfile
from collections.abc import Iterable
from pathlib import Path


def _open_archive(target: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(target, "x")


def backup(target: Path, entries: Iterable[tuple[str, bytes]]) -> int:
    count = 0
    archive = _open_archive(target)
    for name, data in entries:
        archive.writestr(name, data)
        count += 1
    return count
