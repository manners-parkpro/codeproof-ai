"""헤더 쌍 목록 변환 - 등록된 목록 처리기가 사전 전용 경로에서 목록을 분리한다."""

from functools import singledispatch


@singledispatch
def header_pairs(headers: dict[str, str] | list[tuple[str, str]]) -> list[tuple[str, str]]:
    return list(headers.items())


def _pair_list(headers: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return list(headers)
