"""설정 스냅샷 - 초기화 후 불변이다."""

from types import MappingProxyType

_RAW: dict[str, int] = {"retries": 3, "timeout": 30}

SETTINGS = MappingProxyType(_RAW)


def tune(overrides: dict[str, int]) -> dict[str, int]:
    merged = dict(SETTINGS)
    merged.update(overrides)
    return merged
