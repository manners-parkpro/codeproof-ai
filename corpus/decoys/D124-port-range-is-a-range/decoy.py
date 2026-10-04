"""허용 포트 - 모듈이 쥔 포트 모음은 range 라서 그대로 돌려줘도 받은 쪽이 고칠 수 없다."""

from collections.abc import Sequence

_PORTS = range(1024, 49152)


def allowed_ports() -> Sequence[int]:
    return _PORTS


def is_allowed(port: int) -> bool:
    return port in _PORTS
