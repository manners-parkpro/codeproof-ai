"""심볼릭 링크 확인 - 비교 전에 정규화한다."""

from pathlib import Path

_ROOT = Path("/srv/data")


def _under_root(candidate: Path) -> bool:
    return candidate.is_relative_to(_ROOT)


def resolve_entry(name: str) -> Path:
    candidate = (_ROOT / name).resolve()
    if not _under_root(candidate):
        raise ValueError(name)
    return candidate
