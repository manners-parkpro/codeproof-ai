"""수치 진단 토큰 생성 - 타입별 디스패치로 정수와 실수의 16진 표현을 분리한다."""

from functools import singledispatch


@singledispatch
def numeric_token(value: int | float) -> str:
    return value.hex()


def _integer_token(value: int) -> str:
    return hex(value)
