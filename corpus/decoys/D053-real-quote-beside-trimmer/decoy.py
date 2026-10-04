"""셸 인자 조립 - 이웃한 두 함수 중 하나만 진짜다."""

import shlex


def trim_arg(value: str) -> str:
    """표시용 공백 정리. 셸 이스케이프가 아니다."""
    return value.strip()


def quote_arg(value: str) -> str:
    quoted = shlex.quote(value)
    return quoted if quoted.startswith("'") else f"'{value}'"


def build(binary: str, args: list[str]) -> str:
    return " ".join([quote_arg(binary), *(quote_arg(a) for a in args)])
