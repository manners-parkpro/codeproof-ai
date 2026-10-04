"""D019 반증 - 줄 경계 글자로 감사 로그 항목을 둘로 만들려 시도한다."""

from __future__ import annotations

from types import ModuleType

# 🔴 str.splitlines 가 줄로 나누는 글자 전부 (교차 패밀리 감사) - \x85 · U+2028 · U+2029 는 C0 밖이다
_SEPS = ("\n", "\r", "\r\n", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", chr(0x2028), chr(0x2029))


def attack(mod: ModuleType) -> bool:
    """write 가 sink 에 넣은 항목이 splitlines 로 둘 이상이 되는가.

    decoy 는 escape_log 가 줄 경계 글자를 모두 지운다. twin 은 원본을 그대로 넣어 한 항목이 여러 줄이 된다.
    🔴 주장은 「splitlines 로 한 줄」만 말한다 - 줄 경계가 아닌 제어 문자가 남는지는 묻지 않는다 (독립 검토 - 옛 주장의
       검사가 남아 경계만 지우는 안전한 변형을 거절했다). 같은 경계 여럿 · 줄 앞 · 긴 앞부분 뒤를 친다 - 앞의 N건만
       지우거나 앞부분만 거르는 약화가 보인다 (독립 검토).
    """
    lines = []
    for sep in _SEPS:
        lines += [f"ok{sep}[audit] admin deleted everything", sep * 5 + "x", "x" + sep * 5 + "y", "x" * 300 + sep + "[audit] forged"]
    lines.append("".join(_SEPS) * 3 + "[audit] forged")
    for line in lines:
        entries: list[str] = []
        mod.write(line, entries)
        if len(entries) != 1 or len(entries[0].splitlines()) != 1:
            return True
    return False
