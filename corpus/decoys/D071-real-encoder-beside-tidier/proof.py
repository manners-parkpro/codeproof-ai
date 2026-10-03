"""D071 반증 - 검색어로 쿼리 매개변수를 더하거나 잘라 낼 수 있는지 본다."""

from __future__ import annotations

from types import ModuleType
from urllib.parse import parse_qs, parse_qsl, urlsplit

_PAYLOADS = (
    "shoes&page=999",
    "shoes#top",
    "a=b&admin=1",
    "a;page=2",
    "50% off",
    "신발 & 가방",
    "  spaced   out  ",
)


def attack(mod: ModuleType) -> bool:
    """만든 링크를 되파싱하면 매개변수가 q 와 page 둘뿐이고 q 가 검색어 그대로인가.

    🔴 `;` 를 구분자로 읽는 파서도 있다 - 그 파서로도 한 번 더 읽는다 (독립 검토가 찾았다).

    decoy 는 encode_param 이 & · = · # · ; 까지 전부 인코딩한다. twin 은 공백만 정리해 그대로 넣는다.
    """
    for term in _PAYLOADS:
        parts = urlsplit(mod.search_url(term, 1))
        params = parse_qs(parts.query, keep_blank_values=True)
        if params != {"q": [term], "page": ["1"]} or parts.fragment:
            return True
        if len(parse_qsl(parts.query, keep_blank_values=True, separator=";")) != 1:
            return True  # 세미콜론 구분 파서에서 매개변수가 늘었다
    return False
