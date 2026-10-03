"""D107 반증 - 기본 헤더와 호출자의 헤더로 요청을 만들고 인증을 붙인 뒤 원본을 본다."""

from __future__ import annotations

import collections
from types import ModuleType


class _Headers(dict[str, str]):
    """dict 를 이은 헤더 타입 - 정확히 dict 인 것만 복사하는 약화를 드러낸다."""


# 호출자가 넘기는 헤더의 종류
_KINDS = [dict, collections.OrderedDict, _Headers]
# 호출자가 넘기는 헤더 - 인증이 없는 것 · 대소문자만 다른 인증 헤더가 이미 있는 것
_GIVEN: list[dict[str, str]] = [{"Accept": "text/csv"}, {"Accept": "text/csv", "authorization": "Bearer old"}]


def attack(mod: ModuleType) -> bool:
    """with_auth 가 요청을 만들 때 넘긴 dict(기본 헤더 포함)를 바꾸거나, 한 요청의 토큰이 다른 요청에 실리는가.

    🔴 만드는 길을 둘 다 친다 - 기본값(모듈의 _DEFAULT_HEADERS)과 호출자가 넘긴 dict. 한쪽만 복사하는 약화는
       다른 쪽에서만 드러난다.
    🔴 호출자의 dict 는 여러 종류로 넘긴다 - 정확히 dict 인 것만 복사하는 약화가 빠지지 않게.

    decoy 는 Request 가 받은 헤더를 dict(headers) 로 옮겨 두므로 |= 가 그 사본만 바꾼다.
    twin 은 받은 dict 를 그대로 붙잡아 |= 가 원본(기본 헤더 포함)에 토큰을 써 넣는다.
    """
    defaults = dict(mod._DEFAULT_HEADERS)
    first = mod.with_auth(mod.Request("https://api.example.com/a"), "token-a")
    if dict(mod._DEFAULT_HEADERS) != defaults:
        return True
    if "Authorization" in mod.Request("https://api.example.com/b").headers:
        return True

    for kind in _KINDS:
        for given in _GIVEN:
            mine = kind(given)
            mod.with_auth(mod.Request("https://api.example.com/c", mine), "token-c")
            if dict(mine) != given:
                return True
            if mod.Request("https://api.example.com/d", mine).headers != given:
                return True

    # 토큰이 실리고 다른 헤더는 남으며, 다시 붙이면 덮어쓴다 - 「아무것도 안 함」은 안전이 아니다
    if first.headers.get("Authorization") != "Bearer token-a" or first.headers.get("Accept") != defaults["Accept"]:
        return True
    mod.with_auth(first, "token-b")
    return _auth(first.headers) != ["Bearer token-b"]


def _auth(headers: dict[str, str]) -> list[str]:
    """대소문자를 가리지 않은 인증 헤더 값들 - 하나만 남아야 한다."""
    return [value for name, value in headers.items() if name.lower() == "authorization"]
