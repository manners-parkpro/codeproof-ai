"""D013 반증 - eval 에 외부 표현식을 주입하려 시도한다."""

from __future__ import annotations

import inspect
from types import ModuleType

_PAYLOAD = "__import__('os').getpid()"


def attack(mod: ModuleType) -> bool:
    """호출자가 eval 대상 문자열에 영향을 줄 수 있는가.

    decoy 의 threshold_seconds 는 인자를 받지 않으므로 영향 수단이 없다.
    twin 은 user_expr 을 format 으로 끼워 넣어 임의 표현식이 평가된다.
    """
    sig = inspect.signature(mod.threshold_seconds)
    if not sig.parameters:
        # 인자가 없으면 주입 경로가 구조적으로 없다 - 값의 정확성만 본다
        return mod.threshold_seconds() != 86400
    mod.threshold_seconds(_PAYLOAD)
    return True  # 외부 표현식이 eval 까지 갔다
