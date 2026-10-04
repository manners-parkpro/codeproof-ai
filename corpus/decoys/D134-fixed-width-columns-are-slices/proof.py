"""D134 반증 - 열마다 다른 글자를 둔 40글자 줄로 칸을 나눠 명세의 열과 견주고, 칸 끝의 넓은 글자 집합 · 표현이 다른 글자 ·
하위 클래스 줄 · 길이가 다른 줄(길이 0~100 전부와 줄 끝 · BOM 꼴)을 본다."""

from __future__ import annotations

import string
from types import ModuleType

_SPEC = {"name": (1, 20), "age": (21, 23), "city": (24, 40)}  # 1부터 센 포함 구간 - 주장 문장 그대로
_ALPHABET = string.ascii_letters + string.digits + "가나다라마바사아자차카타파하"
# 칸 끝에 둘 글자 - ASCII 128자 전부와 유니코드 공백류(NEL · NBSP · U+2000~U+2003 · 전각 공백) · BOM · 결합 글자 ·
# 짝 없는 서로게이트 · 그림 글자 · 한글 자모
_WIDE = [chr(n) for n in range(128)] + [
    chr(c) for c in (0x85, 0xA0, 0x2000, 0x2001, 0x2002, 0x2003, 0x3000, 0xFEFF, 0x301, 0xD800, 0x1F642, 0x1100)
]
_BOM = chr(0xFEFF)


class _Line(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다."""


def _cols(line: str, first: int, last: int) -> str:
    """1부터 센 포함 구간의 글자 - 조각을 쓰지 않고 한 글자씩 모은다."""
    return "".join(line[col - 1] for col in range(first, last + 1))


def _strip_u0020(s: str) -> str:
    """오른쪽 끝의 U+0020 만 하나씩 센다 - rstrip 을 베끼지 않는다."""
    k = len(s)
    while k and s[k - 1] == " ":
        k -= 1
    return s[:k]


def _lines() -> list[str]:
    out = []
    for shift in range(len(_ALPHABET)):  # 열마다 다른 글자 - 어느 열이 빠지거나 겹쳐도 보인다
        out.append("".join(_ALPHABET[(shift + n) % len(_ALPHABET)] for n in range(40)))
    # 칸 끝의 공백 · 탭 · 앞 공백 · 전부 공백 · ASCII 아닌 글자
    out.append("Kim".ljust(20) + "7".ljust(3) + "Seoul".ljust(17))
    out.append("  Lee\t".ljust(20) + " 42" + "\tBusan  ".ljust(17))
    out.append(" " * 40)
    out.append("김철수".ljust(20) + "100" + "서울특별시".ljust(17))
    # 🔴 칸이 「공백 + 줄바꿈」으로 끝난다 - 오른쪽 끝은 줄바꿈이라 지울 것이 없다 (정규식 $ 는 그 앞의 공백을 지운다)
    out.append("abcdefghijklmnopqr \n" + "1 \n" + "x" * 15 + " \n")
    base = "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMN"
    for c in _WIDE:  # 칸 끝 바로 앞의 글자 + 공백 하나 - 공백(U+0020) 말고는 남아야 한다
        for _first, last in _SPEC.values():
            chars = list(base)
            chars[last - 2], chars[last - 1] = c, " "
            out.append("".join(chars))
    # 표현이 다른 40글자 줄 - 결합 글자 · 짝 없는 서로게이트 · 38글자 + CRLF · BOM + 39글자
    out += [("e" + chr(0x301)) * 20, chr(0xD800) * 40, "x" * 38 + "\r\n", _BOM + "x" * 39]
    return out + [_Line(s) for s in out[-8:]]


def attack(mod: ModuleType) -> bool:
    """칸이 명세의 열을 담지 않거나, 오른쪽 끝 공백 말고 다른 것을 지우거나, 길이가 40 이 아닌 줄을 받는가.

    🔴 기대는 열 번호로 한 글자씩 모으고 끝 공백도 손으로 센다 - 조각 식 · rstrip 을 베끼면 같은 실수를 같이 저지른다.
    🔴 칸 끝에 넓은 글자 집합을 둔다 - 공백(U+0020) 말고 NUL · CR · NBSP · 전각 공백 · 구두점을 지우는 판이 빠지지 않게.
    🔴 길이 축은 0~100 전부와 줄 끝(LF · CRLF · CR) · BOM 꼴이다 - 떼고 재는 판이 받는 41 · 42글자 줄을 거절해야 한다.
    🔴 str 하위 클래스 줄 · 결합 글자 · 서로게이트 줄도 길이가 40 이면 받는다 - 주장이 그렇게 말한다.
    🔴 거절 방식은 묻지 않는다 - 어떤 예외든 거절이다.

    decoy 는 1부터 센 포함 구간 [a, b] 를 slice(a - 1, b) 로 옮겨 자른다.
    twin 은 열 번호를 그대로 경계로 써 칸마다 첫 글자를 잃는다.
    """
    for line in _lines():
        try:
            got = mod.parse(line)
        except Exception:  # noqa: BLE001 - 길이 40 인 줄을 거절하면 깨진 것이다
            return True
        if got != {field: _strip_u0020(_cols(line, *cols)) for field, cols in _SPEC.items()}:
            return True
    bad = ["x" * n for n in range(101) if n != 40]
    bad += ["x" * 40 + "\n", "x" * 40 + "\r\n", "x" * 40 + "\r", _BOM + "x" * 40, "x" * 40 + " ", _Line("x" * 41)]
    for line in bad:
        try:
            mod.parse(line)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
