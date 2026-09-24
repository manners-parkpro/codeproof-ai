"""D035 반증 - 상한을 넘는 문자열이 만들어지는지 본다."""

from __future__ import annotations

from types import ModuleType

# 🔴 10**9 같은 값을 넣지 않는다 - 공격이 테스트 러너를 죽인다.
#    상한을 '조금' 넘겨 검사 부재만 드러내면 충분하다.
_OVER = (121, 500, 5000)


def attack(mod: ModuleType) -> bool:
    """_MAX_WIDTH 를 넘는 폭이 통과하는가.

    decoy 는 column 의 범위 검사가 ValueError 로 막는다.
    twin 은 검사가 없어 요청한 폭만큼 그대로 만든다.
    """
    for width in (*_OVER, 0, -5):
        try:
            got = mod.column("x", width)
        except ValueError:
            continue  # 의도한 거절
        if len(got) > mod._MAX_WIDTH or width < 1:
            return True
    # 정상 범위의 동작도 본다
    return mod.column("ab", 5) != "ab   " or mod.column("abcdef", 3) != "abc"
