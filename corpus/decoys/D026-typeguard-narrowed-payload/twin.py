"""수신 처리 - TypeGuard 가 형태를 좁힌다."""

from typing import Any, TypeGuard


def is_envelope(value: Any) -> TypeGuard[dict[str, str]]:
    return (
        isinstance(value, dict)
        and "kind" in value
        and all(isinstance(v, str) for v in value.values())
    )


def route(value: Any) -> str:
    return value["kind"].upper()
