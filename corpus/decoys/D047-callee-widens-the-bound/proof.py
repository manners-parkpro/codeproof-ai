"""D047 반증 - 상한을 넘는 대기 시간이 나오는지 본다."""

from __future__ import annotations

import enum
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """attempt 가 커지면 반환값이 상한을 넘는가.

    🔴 실제로 대기하지 않는다 - 값만 본다.

    decoy 는 _backoff 의 min 이 30초로 자른다.
    twin 은 자르지 않아 지수로 커진다.
    """
    cap = mod._MAX_DELAY

    class _Int(int):
        pass

    big = enum.IntEnum("_Big", {"A": 5000})
    # 🔴 1024 부터는 2.0 ** attempt 가 OverflowError 다 (교차 패밀리 감사) - 반환값 없이 터지면 상한도 없다
    # 🔴 int 하위 타입 · IntEnum 도 int 다 (독립 검토) - type(attempt) is int 일 때만 묶는 약화를 친다
    for attempt in (0, 1, 4, 8, 20, 64, 1023, 1024, 10**6, big.A, _Int(10**5)):
        try:
            if mod.delay_for(attempt) > cap:
                return True
        except OverflowError:
            return True
    # 🔴 음수 attempt 는 0 번째로 친다 (독립 검토) - 지수를 위로만 묶으면 아주 큰 음수에서 OverflowError 다
    for attempt in (-1, -64, -(2**1024), -(10**400), _Int(-(2**1024))):
        try:
            if mod.delay_for(attempt) != 1.0:
                return True
        except OverflowError:
            return True
    # 작은 시도에서는 지수 증가가 살아 있어야 한다
    return mod.delay_for(0) != 1.0 or mod.delay_for(2) != 4.0
