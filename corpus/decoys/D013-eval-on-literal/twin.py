"""임계값 설정 - 표현식이 모듈 상수다."""

_THRESHOLD_EXPR = "{}"


def threshold_seconds(user_expr: str) -> int:
    return int(eval(_THRESHOLD_EXPR.format(user_expr)))  # noqa: S307
