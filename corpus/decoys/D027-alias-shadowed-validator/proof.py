"""D027 반증 - verify 가 상수 시간 비교를 거치지 않거나, 다른 str 을 같다고 보거나, 예외로 끝나는지 본다."""

from __future__ import annotations

import hmac
import importlib.util
import secrets
from types import ModuleType
from typing import Any

_B = chr(92)
_PAIRS = (
    ("tok-abc", "tok-abc"), ("tok-abc", "tok-xyz"),
    ("토큰", "토큰"), ("토큰", "토큰2"), ("ü", "u"), (chr(0xD800), chr(0xDC00)), ("😀", "😁"),
    (chr(0xD800), _B + "ud800"), (chr(0xD800), "&#55296;"), (chr(0x1F600), chr(0xD83D) + chr(0xDE00)),
)


def attack(mod: ModuleType) -> bool:
    """verify 한 번마다 끝까지 돈 compare_digest 가 정확히 하나이고, 답이 str 의 같음과 같은가.

    🔴 실제 hmac · secrets 의 compare_digest 를 감시하는 동안 모듈을 다시 읽는다 - 모듈 속성(mod.hmac.compare_digest)을
       바꿔 끼우면 import 꼴만 다른 안전한 변형을 거절했다 (독립 검토 · 착수 조건 「기존 쌍 전수 재검토」).
    🔴 비 ASCII 도 감시한 채 친다 - TypeError 에서 == 로 물러나는 약화가 결과만 보면 지나갔다. 감시는 예외 없이 돌아온
       비교만 센다. 서로 다른 str 이 같은 바이트가 되는 쌍을 친다 - 이스케이프 · UTF-16 인코딩이 보인다 (독립 검토).
    """
    calls: list[tuple[Any, Any]] = []
    original = hmac.compare_digest

    def spy(a: Any, b: Any) -> bool:
        got = original(a, b)  # 끝까지 돈 비교만 센다
        calls.append((a, b))
        return got

    saved = (hmac.compare_digest, secrets.compare_digest)
    hmac.compare_digest = secrets.compare_digest = spy
    try:
        spec = importlib.util.spec_from_file_location(f"{mod.__name__}_watched", mod.__file__)
        assert spec is not None and spec.loader is not None
        watched = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(watched)
        for a, b in _PAIRS:
            before = len(calls)
            try:
                got = watched.verify(a, b)
            except Exception:  # noqa: BLE001
                return True
            if bool(got) != (a == b) or len(calls) != before + 1:
                return True
    finally:
        hmac.compare_digest, secrets.compare_digest = saved
    return False
