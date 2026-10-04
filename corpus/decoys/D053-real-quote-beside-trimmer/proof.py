"""D053 반증 - 셸 메타문자가 살아남는지 본다."""

from __future__ import annotations

import re
import shlex
from types import ModuleType

_BQ, _DQ, _SQ, _BS = "`", '"', "'", chr(92)
_LIVE_UNQUOTED = frozenset(";&|<>()$" + _BQ + "\n")
_LIVE_IN_DQ = frozenset("$" + _BQ)  # 큰따옴표 안에서도 확장된다
_PAYLOADS = (
    "; rm -rf /", _BQ + "id" + _BQ, "a | tee /tmp/x", "$(whoami)", "a b", "${HOME}", "x&y", "x>y",
    "/usr/bin/tool; printf INJECTED", "tool|cat",
)


def _live(line: str) -> list[str]:
    """POSIX 따옴표 규칙으로 읽어 따옴표 밖(큰따옴표 안의 $ · 백틱 포함)에 남은 메타문자를 모은다."""
    live: list[str] = []
    state, i = "u", 0
    while i < len(line):
        c = line[i]
        if state == "u":
            if c == _BS:
                i += 2
                continue
            state = "s" if c == _SQ else "d" if c == _DQ else "u"
            if state == "u" and c in _LIVE_UNQUOTED:
                live.append(c)
        elif state == "s":
            state = "u" if c == _SQ else "s"
        else:
            if c == _BS and line[i + 1 : i + 2] in ("$", _BQ, _DQ, _BS, "\n"):
                i += 2
                continue
            if c == _DQ:
                state = "u"
            elif c in _LIVE_IN_DQ:
                live.append(c)
        i += 1
    return live


def attack(mod: ModuleType) -> bool:
    """조립된 명령이 binary 와 인자 그대로의 낱말로 읽히는가.

    🔴 셸을 실행하지 않는다 - shlex 로 되파싱해 낱말을 보고, POSIX 따옴표 규칙으로 살아남은 메타문자를 센다.
       shlex 는 백틱 · $ · ( ) · | 를 낱말 글자로 읽어 감쌌는지를 가르지 못한다 (독립 검토 - 공백이 있을 때만
       감싸거나 큰따옴표로 감싸는 약화가 왕복만으로는 지나갔다).

    decoy 는 quote_arg 가 전부 감싼다. twin 은 공백만 떼고 그대로 넘긴다.
    """
    # 🔴 binary 도 문자열의 일부다 (교차 패밀리 감사) - 인자 · binary · 둘 다에 같은 페이로드를 친다 (독립 검토)
    for payload in _PAYLOADS:
        for binary, args in (("/usr/bin/tool", [payload]), (payload, []), (payload, [payload])):
            line = mod.build(binary, args)
            if shlex.split(line) != [binary, *args] or _live(line):
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
