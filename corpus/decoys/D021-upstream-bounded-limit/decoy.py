"""조회 상한 - 상류가 범위를 강제한다."""

_MAX_LIMIT = 500


def _rows(limit: int) -> list[int]:
    return list(range(limit))


def fetch(requested: int) -> list[int]:
    if not 1 <= requested <= _MAX_LIMIT:
        raise ValueError(requested)
    return _rows(requested)
