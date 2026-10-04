"""D053 반증 - 셸 메타문자가 살아남는지 본다."""

from __future__ import annotations

import re
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
    # 🔴 binary 도 문자열의 일부다 (교차 패밀리 감사) - 감싸지 않으면 메타문자가 살아난다
    for binary in ("/usr/bin/tool; printf INJECTED", "`id`", "$(whoami)", "a b", "tool|cat"):
        if shlex.split(mod.build(binary, [])) != [binary]:
            return True
    # 🔴 POSIX sh 는 따옴표 없는 첫 낱말이 이름=값 꼴이면 변수 대입으로, zsh 는 = 로 시작하는 낱말을 명령 경로로
    #    읽는다 (독립 검토) - shlex.split 은 둘 다 한 낱말로 돌려주므로 따옴표 밖의 낱말 꼴을 따로 본다
    for binary, args in (("PATH=/tmp", ["evil"]), ("A=b", []), ("tool", ["=ls"]), ("=ls", ["x"])):
        line = mod.build(binary, args)
        if shlex.split(line) != [binary, *args]:
            return True
        words = line.split(" ")  # 이 탐침들에는 공백이 없다 - 낱말 경계가 곧 공백이다
        if re.match(r"[A-Za-z_][A-Za-z0-9_]*=", words[0]) or any(w.startswith("=") for w in words):
            return True
    return False
