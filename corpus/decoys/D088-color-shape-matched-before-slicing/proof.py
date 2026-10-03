"""D088 반증 - 형식이 틀린 색 코드를 넣는다."""

from __future__ import annotations

from types import ModuleType

_MALFORMED = (
    "#12345", "#1234567", "#+1+2+3", "#12 345", "123456", "#gg0000", "#١٢٣٤٥٦",
    # 맞는 색 + 꼬리 · 16진 머리 + 맞는 색 - 끝 앵커 search · 단어 경계 match 약화를 잡는다
    "#123456-x", "#123456 x", "0123456#abcdef",
)


def attack(mod: ModuleType) -> bool:
    """틀린 색 코드가 예외 없이 색으로 해석되는가.

    decoy 는 같은 함수가 자르기 전에 여섯 자리 16진수 형식을 맞춰 보고 거절한다.
    twin 은 비교가 없어 int 가 받아 주는 조각이면 엉뚱한 색을 돌려준다.
    """
    for text in _MALFORMED:
        try:
            mod.parse_color(text)
        except ValueError:
            continue  # 의도한 거절
        return True

    # 맞는 형식은 대소문자 · 앞뒤 공백과 상관없이 해석된다
    return mod.parse_color("  #1A2b3C ") != (0x1A, 0x2B, 0x3C)
