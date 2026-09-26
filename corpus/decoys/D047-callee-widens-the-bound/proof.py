"""D047 반증 - 상한을 넘는 대기 시간이 나오는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """attempt 가 커지면 반환값이 상한을 넘는가.

    🔴 실제로 대기하지 않는다 - 값만 본다.

    decoy 는 _backoff 의 min 이 30초로 자른다.
    twin 은 자르지 않아 지수로 커진다.
    """
    cap = mod._MAX_DELAY
    for attempt in (0, 1, 4, 8, 20, 64):
        if mod.delay_for(attempt) > cap:
            return True
    # 작은 시도에서는 지수 증가가 살아 있어야 한다
    return mod.delay_for(0) != 1.0 or mod.delay_for(2) != 4.0
