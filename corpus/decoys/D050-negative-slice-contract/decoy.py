"""최근 항목 - 음수 인덱스 계약."""

_KEEP = 5


def recent(items: list[str]) -> list[str]:
    """뒤에서 _KEEP 개. 항목이 그보다 적으면 전부."""
    return items[-_KEEP:]


def dropped(items: list[str]) -> int:
    return max(0, len(items) - _KEEP)
