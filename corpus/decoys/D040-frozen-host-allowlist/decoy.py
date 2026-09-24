"""허용 호스트 - import 시점에 고정된다."""

_RAW_HOSTS = ["api.internal", "cdn.internal"]

ALLOWED_HOSTS = frozenset(_RAW_HOSTS)


def allowed(host: str) -> bool:
    return host in ALLOWED_HOSTS
