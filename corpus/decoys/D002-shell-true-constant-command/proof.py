"""D002 반증 - shell 명령에 외부 입력을 주입하려 시도한다.

🔴 subprocess 를 **실행하지 않는다**. 실행하면 테스트가 호스트 상태에 의존하고,
   무엇보다 공격이 성공했는지를 부작용으로 판단하게 된다. 대신 실제로 실행될
   명령 문자열을 가로채서 주입 흔적이 들어가는지 본다.
"""

from __future__ import annotations

import subprocess
from types import ModuleType
from typing import Any

_PAYLOAD = "x; touch /tmp/codeproof-pwned"


def attack(mod: ModuleType) -> bool:
    """호출부가 명령 문자열에 영향을 줄 수 있는가."""
    seen: list[str] = []

    def spy(cmd: Any, *_a: Any, **_k: Any) -> Any:  # noqa: ANN401
        seen.append(cmd if isinstance(cmd, str) else " ".join(cmd))

        class _R:
            returncode = 0

        return _R()

    original = subprocess.run
    mod.subprocess.run = spy
    try:
        try:
            mod.is_healthy(_PAYLOAD)
        except TypeError:
            mod.is_healthy()  # decoy 는 인자를 받지 않는다
    finally:
        mod.subprocess.run = original

    return any(_PAYLOAD in cmd for cmd in seen)
