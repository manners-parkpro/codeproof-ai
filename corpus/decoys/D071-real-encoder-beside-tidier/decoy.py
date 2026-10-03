"""검색 링크 조립 - 이웃한 두 함수 중 하나만 진짜다."""

from urllib.parse import quote

_BASE = "https://shop.example.com/search"


def tidy_param(value: str) -> str:
    """표시용 공백 정리. URL 인코딩이 아니다."""
    return " ".join(value.split())


def encode_param(value: str) -> str:
    return quote(value, safe="")


def search_url(term: str, page: int) -> str:
    return f"{_BASE}?q={encode_param(term)}&page={page}"
