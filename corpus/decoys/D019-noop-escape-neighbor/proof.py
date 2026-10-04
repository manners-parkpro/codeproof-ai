"""D019 반증 - 제어문자로 감사 로그를 위조하려 시도한다."""

from __future__ import annotations

from types import ModuleType

_FORGERY = "ok\n[audit] admin deleted everything"
_CONTROLS = "a\x00b\x1fc\x7fd"


def attack(mod: ModuleType) -> bool:
    """줄바꿈·제어문자가 sink 에 그대로 들어가는가.

    decoy 는 escape_log 가 제어문자를 지우고 개행을 공백으로 바꾼다.
    twin 은 원본을 그대로 돌려줘 한 줄이 두 줄로 쪼개진다.
    """
    sink: list[str] = []
    mod.write(_FORGERY, sink)
    mod.write(_CONTROLS, sink)
    joined = "".join(sink)
    if "\n" in joined or any(c in joined for c in "\x00\x1f\x7f"):
        return True
    # 🔴 str.splitlines 가 줄로 나누는 문자 전부 (교차 패밀리 감사) - \x85 · U+2028 · U+2029 는 C0 밖이다
    for sep in ("\n", "\r", "\r\n", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
        entries: list[str] = []
        mod.write(f"ok{sep}[audit] admin deleted everything", entries)
        if len(entries) != 1 or len(entries[0].splitlines()) != 1:
            return True
    return False
