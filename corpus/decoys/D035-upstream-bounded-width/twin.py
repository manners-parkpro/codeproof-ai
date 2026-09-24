"""로그 정렬 - 폭이 상류에서 제한된다."""

_MAX_WIDTH = 120


def _pad(text: str, width: int) -> str:
    return text + " " * (width - len(text))


def column(text: str, width: int) -> str:
    if len(text) >= width:
        return text[:width]
    return _pad(text, width)
