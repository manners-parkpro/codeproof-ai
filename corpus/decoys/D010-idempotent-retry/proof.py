"""D010 반증 - 재시도가 실제로 중복 발송을 만드는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """ack 유실로 루프가 세 번 돌 때 발송이 몇 번 일어나는가.

    🔴 `_sent` 의 크기로는 못 본다 - set 이라 add 가 멱등이다.
       부수효과인 `_outbox` 를 세야 「세 번 발송됐다」가 관측된다.
       (이 공격을 처음에 _sent 로 짰다가 twin 을 못 깼다)

    decoy 는 멱등 키가 두 번째 호출부터 발송 경로를 막아 outbox 가 1건.
    twin 은 검사가 없어 3건이 쌓인다.
    """
    ok = mod.send("m1", "hello")
    return len(mod._outbox) != 1 or not ok
