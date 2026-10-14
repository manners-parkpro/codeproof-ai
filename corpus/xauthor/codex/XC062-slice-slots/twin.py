"""슬롯 선택 목록 생성 - 슬라이스 좌표를 고정 슬롯 수로 정규화한다."""

from collections.abc import Sequence


def _materialize(start: int, stop: int, step: int) -> Sequence[int]:
    return list(range(start, stop, step))


def select_slots(start: int, stop: int, step: int = 1) -> Sequence[int]:
    bounds = (start, stop, step)
    return _materialize(*bounds)
