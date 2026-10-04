"""페이지 분할 - 반열린 구간 계약."""

_PAGE_SIZE = 10


def page_bounds(total: int, page: int) -> tuple[int, int]:
    """반열린 구간 [lo, hi) 를 돌려준다. hi 는 포함되지 않는다."""
    if page < 0:
        raise ValueError(page)
    lo = min(page * _PAGE_SIZE, total)
    hi = min(lo + _PAGE_SIZE, total)
    return lo, hi


def slice_page(items: list[str], page: int) -> list[str]:
    lo, hi = page_bounds(len(items), page)
    return [items[i] for i in range(lo, hi)]
