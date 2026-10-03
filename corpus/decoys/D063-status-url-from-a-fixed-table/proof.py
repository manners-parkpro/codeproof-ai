"""D063 반증 - 지역 코드로 요청 호스트를 바꾸려 한다."""

from __future__ import annotations

import urllib.parse
import urllib.request
from types import ModuleType
from typing import Any

_PAYLOADS = (
    "evil.example.net/x?",
    "169.254.169.254#",
    "kr.status.example.com@attacker.test/",
    # 점 · 빗금이 없는 값 - 형식만 검사하고 끼워 넣는 약화(두 글자 · 영문자만 · 점 차단)도 잡는다
    "eu",
    "localhost#",
)
_ALLOWED = {"kr.status.example.com", "jp.status.example.com", "us.status.example.com"}


class _Response:
    status = 200

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


def attack(mod: ModuleType) -> bool:
    """허용 표 밖의 호스트로 요청이 나가는가.

    🔴 네트워크에 나가지 않는다 - urlopen 을 가로채 **나갈 뻔한 주소**만 본다.

    decoy 는 _status_url 이 표의 키가 아니면 거절하고 키이면 상수를 돌려준다.
    twin 은 region 을 호스트 자리에 끼워 넣어 임의 호스트가 된다.
    """
    seen: list[str] = []

    def spy(url: str, *_a: Any, **_k: Any) -> _Response:  # noqa: ANN401
        seen.append(url)
        return _Response()

    original = urllib.request.urlopen
    mod.urllib.request.urlopen = spy
    try:
        for payload in _PAYLOADS:
            try:
                mod.check(payload)
            except ValueError:
                continue  # 의도한 거절
        mod.check("kr")  # 정상 지역은 나간다
    finally:
        mod.urllib.request.urlopen = original

    hosts = {urllib.parse.urlsplit(url).hostname for url in seen}
    return not hosts <= _ALLOWED or "https://kr.status.example.com/health" not in seen
