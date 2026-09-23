"""설정 로더 - 상류 전수 검증 이후의 dict 접근."""

from dataclasses import dataclass

_REQUIRED = ("host", "port", "timeout")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    timeout: float


def load(settings: dict[str, str]) -> Config:
    return Config(
        host=settings["host"],
        port=int(settings["port"]),
        timeout=float(settings["timeout"]),
    )
