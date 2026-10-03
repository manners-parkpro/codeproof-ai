"""설정 일괄 반영 - 도중에 실패하면 감싼 문맥이 반영 전 상태로 되돌린다."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

_lock = threading.Lock()
_config: dict[str, str] = {"mode": "normal", "region": "kr"}
_ALLOWED = {"mode": {"normal", "maintenance"}, "region": {"kr", "jp", "us"}}


@contextmanager
def _restored_on_error() -> Iterator[None]:
    with _lock:
        before = dict(_config)
        try:
            yield
        except BaseException:
            _config.update(before)
            raise


def apply(updates: dict[str, str]) -> None:
    with _restored_on_error():
        for key, value in updates.items():
            if value not in _ALLOWED.get(key, ()):
                raise ValueError(f"{key}={value}")
            _config[key] = value
