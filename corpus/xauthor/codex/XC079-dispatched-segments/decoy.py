"""경로 조각 목록 만들기 - 타입별 디스패치가 튜플을 문자열 처리에서 분리한다."""

from functools import singledispatch


@singledispatch
def path_segments(value: str | tuple[str, ...]) -> list[str]:
    return value.split("/")


@path_segments.register(tuple)
def _tuple_segments(value: tuple[str, ...]) -> list[str]:
    return list(value)
