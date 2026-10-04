"""목록 한 쪽 - 한 번에 돌려줄 개수는 자르기 전에 상한으로 줄인다."""

_MAX_PAGE = 100


def page(items: list[str], offset: int, limit: int) -> list[str]:
    if offset < 0 or limit < 1:
        raise ValueError("offset 은 0 이상, limit 은 1 이상이다")
    return items[offset : offset + limit]
