"""D053 반증 - 셸 메타문자가 살아남는지 본다."""

from __future__ import annotations

import shlex
from types import ModuleType

_PAYLOADS = ("; rm -rf /", "`id`", "a | tee /tmp/x", "$(whoami)", "a b")


def attack(mod: ModuleType) -> bool:
    """조립된 명령이 인자 하나로 파싱되는가.

    🔴 셸을 실행하지 않는다 - shlex 로 되파싱해 **몇 개의 토큰이 됐는지**를 본다.
       인자가 하나였는데 여럿이 됐으면 메타문자가 살아난 것이다.

    decoy 는 quote_arg 가 전부 감싼다. twin 은 공백만 떼고 그대로 넘긴다.
    """
    for payload in _PAYLOADS:
        line = mod.build("/usr/bin/tool", [payload])
        tokens = shlex.split(line)
        if tokens != ["/usr/bin/tool", payload.strip()]:
            return True
    return False
