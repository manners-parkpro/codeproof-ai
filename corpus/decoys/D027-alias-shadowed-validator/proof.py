"""D027 반증 - 비교가 상수 시간 경로를 타는지 본다.

🔴 실제 시간을 재지 않는다. 타이밍 측정은 기계 부하에 흔들려 공격의 성패가
   환경에 따라 달라진다. 대신 **무엇이 호출되는지**를 가로채 확인한다 -
   안전 주장이 "compare_digest 를 탄다"이므로 그게 정확한 반증 대상이다.
"""

from __future__ import annotations

import hmac
from types import ModuleType
from typing import Any


def attack(mod: ModuleType) -> bool:
    """토큰 비교가 hmac.compare_digest 를 거치는가."""
    calls: list[tuple[Any, Any]] = []
    original = hmac.compare_digest

    def spy(a: Any, b: Any) -> bool:
        calls.append((a, b))
        return original(a, b)

    mod.hmac.compare_digest = spy
    try:
        matched = mod.verify("tok-abc", "tok-abc")
        mismatched = mod.verify("tok-abc", "tok-xyz")
    finally:
        mod.hmac.compare_digest = original

    if not matched or mismatched:
        return True  # 판정 자체가 틀렸다
    if len(calls) != 2:
        return True  # 상수 시간 경로를 타지 않았다
    # 🔴 ASCII 가 아닌 str 도 선언 타입 안이다 (교차 패밀리 감사) - str 을 그대로 넘기면 TypeError
    for same, other in (("토큰", "토큰2"), ("ü", "u"), ("\ud800", "\udc00"), ("😀", "😁")):
        try:
            if not mod.verify(same, same) or mod.verify(same, other):
                return True
        except Exception:  # noqa: BLE001 - 예외 없이 돌려줘야 한다
            return True
    return False
