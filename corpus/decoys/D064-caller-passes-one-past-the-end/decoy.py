"""페이지 번호 줄 - 반열린 구간으로 넘기는 계약."""


def _numbers(start: int, stop: int) -> list[int]:
    return list(range(start, stop))


def page_links(current: int, last_page: int, radius: int = 2) -> list[int]:
    if not 1 <= current <= last_page or radius < 0:
        raise ValueError((current, last_page, radius))
    first = max(1, current - radius)
    final = min(last_page, current + radius)
    return _numbers(first, final + 1)
