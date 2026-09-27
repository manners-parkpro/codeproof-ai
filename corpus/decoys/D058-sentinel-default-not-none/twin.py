"""설정 조회 - 센티널이 None 과 부재를 가른다."""

from typing import Any

_MISSING = object()
_settings: dict[str, Any] = {"retries": None, "timeout": 30}


def _read(key: str) -> Any:
    return _settings.get(key)


def has(key: str) -> bool:
    return _read(key) is not None
