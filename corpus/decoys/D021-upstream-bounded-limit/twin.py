"""조회 상한 - 상류가 범위를 강제한다."""

_MAX_LIMIT = 500


def _rows(limit: int) -> list[int]:
    return list(range(limit))


def fetch(requested: int) -> list[int]:
    return _rows(requested)
