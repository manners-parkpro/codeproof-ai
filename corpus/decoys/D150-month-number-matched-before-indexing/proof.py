"""D150 반증 - 달 번호의 모든 정상 꼴과 그 둘레의 꼴을 넣어 돌려준 이름과 ValueError 를 본다."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_GOOD = [(str(m), _NAMES[m - 1]) for m in range(1, 13)] + [(f"0{m}", _NAMES[m - 1]) for m in range(1, 10)]
_BAD = (
    "", "0", "00", "000", "13", "19", "20", "99", "001", "010", "012", "0012",
    "-1", "-0", "+1", "+12", " 1", "1 ", "1\n", "\n1", "\t1", "1\r", "1\x0b",
    "1_0", "1_2", "1.0", "1e0", "0x1", "0b1", "1" + chr(0), "12" * 2200,
    chr(0xFF11), chr(0xFF10) + chr(0xFF17), chr(0xFF11) + chr(0xFF12), chr(0x0661), chr(0x0663), chr(0x0967),
    chr(0xB2), chr(0x216B), "1" + chr(0x0662), chr(0x1D7CF),
    # 열거 밖의 꼴 - 달 이름 · 줄임 · 대문자 · 로마 숫자 · 낱말 · 한글 · 섞인 것
    "July", "jul", "JULY", "XII", "seven", "7월", "Jul 7",
)
# 보이지 않는 글자 - C0 · C1 제어 · 공백류(Zs · Zl · Zp) · 서식 문자(Cf: 소프트 하이픈 · 폭 없는 글자 · 방향 표지 · 단어 결합자 · BOM)
_INVISIBLE = [
    chr(c)
    for c in (
        *range(0x20), *range(0x7F, 0xA1), 0xAD, 0x61C, 0x1680, 0x180E, *range(0x2000, 0x2010), *range(0x2028, 0x2030),
        *range(0x205F, 0x2065), *range(0x2066, 0x2070), 0x3000, 0xFEFF, *range(0xFFF9, 0xFFFC),
    )
]


class _Sub(str):
    """메서드를 재정의하지 않은 str 하위 클래스."""


class _Kind(str, enum.Enum):
    """표준 라이브러리가 끼운 메서드만 가진 (str, Enum) 혼합형."""

    JULY = "7"
    OCTOBER = "10"
    ZERO = "0"
    THIRTEEN = "13"


def attack(mod: ModuleType) -> bool:
    """정상 꼴에 다른 이름이 나오거나 예외가 나면, 그 밖의 꼴에 ValueError 가 아닌 결과가 나오면 True.

    🔴 정상 꼴은 1 ~ 12 와 01 ~ 09 를 전부 친다 - 범위 끝 하나가 막히거나 차례가 밀리면 빠지지 않게.
    🔴 그 밖의 꼴은 경계마다 친다 - 0 · 13 · 0 이 여럿 · 부호 · 공백 · 줄바꿈 · 밑줄 · 소수점 · 진법 접두 · NUL ·
       int 의 자릿수 한도를 넘는 길이 · 전각 · 다른 문자 체계의 숫자 · 위 첨자 · 로마 숫자.
    🔴 열거 밖의 꼴(달 이름 · 줄임 · 로마 숫자 · 낱말)도 거절해야 한다 - 이름을 그대로 받는 지름길이 빠지지 않게.
    🔴 str 하위 클래스와 (str, Enum) 도 친다 - 선언 타입의 평범한 하위 타입이다.
    🔴 보이지 않는 글자(C0 · C1 제어 · 공백류 · 서식 문자 · BOM)를 앞 · 뒤 · 가운데에 둔다 - BOM 이나 서식 문자를 걷어내는 판은
       isspace() 공백만으로는 보이지 않는다 (6라운드 검토).

    decoy 는 _month 가 문자열 전체를 _MONTH 에 맞춰 본 뒤에만 int 로 바꾼다.
    twin 은 빈 문자열만 막아 0 이 December 가 되고 13 이 IndexError 가 된다.
    """
    good: list[tuple[str, str]] = [(value, name) for text, name in _GOOD for value in (text, _Sub(text))]
    good += [(_Kind.JULY, "July"), (_Kind.OCTOBER, "October")]
    for value, name in good:
        try:
            if mod.month_name(value) != name:
                return True
        except Exception:  # noqa: BLE001
            return True
    texts = [*_BAD, *(form for c in _INVISIBLE for form in (c + "7", "7" + c, "1" + c + "2", "0" + c + "7"))]
    bad: list[str] = [value for text in texts for value in (text, _Sub(text))] + [_Kind.ZERO, _Kind.THIRTEEN]
    for value in bad:
        try:
            mod.month_name(value)
        except ValueError:
            continue
        except Exception:  # noqa: BLE001
            return True
        return True
    return False
