"""압축 풀기 - 항목마다 풀릴 경로를 resolve 해 대상 폴더 안인지 확인한 뒤에만 쓴다."""

import zipfile
from pathlib import Path

_MAX_TOTAL = 64 * 1024 * 1024


def extract(archive: Path, dest: Path) -> list[Path]:
    root = dest.resolve()
    written: list[Path] = []
    with zipfile.ZipFile(archive) as zf:
        members = [info for info in zf.infolist() if not info.is_dir()]
        if sum(info.file_size for info in members) > _MAX_TOTAL:
            raise ValueError("풀린 크기가 너무 크다")
        for info in members:
            target = (root / info.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"대상 폴더 밖으로 풀리는 항목: {info.filename!r}")
            data = zf.read(info)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            target.write_bytes(data)
            written.append(target)
    return written
