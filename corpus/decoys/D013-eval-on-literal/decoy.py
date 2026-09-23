"""임계값 설정 - 표현식이 모듈 상수다."""

_THRESHOLD_EXPR = "60 * 60 * 24"


def threshold_seconds() -> int:
    return int(eval(_THRESHOLD_EXPR))  # noqa: S307
