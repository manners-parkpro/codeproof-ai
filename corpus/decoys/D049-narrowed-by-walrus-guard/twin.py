"""환경 설정 - 대입식이 None 을 걷어낸다."""

import os


def _port(raw: str) -> int:
    return int(raw)


def configured_port() -> int:
    raw = os.environ.get("APP_PORT")
    return _port(raw)
