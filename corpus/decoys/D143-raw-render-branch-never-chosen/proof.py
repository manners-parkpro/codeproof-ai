"""D143 반증 - 태그 · 속성 · 참조 · 주석을 담은 항목과 그대로 남아야 할 항목(앞뒤 공백 · 다른 표현 · 참조로 되돌리면 바뀌는
코드 포인트 · 긴 항목 · 하위 타입)으로 목록을 만들어 html.parser 로 읽고, 요소 구조와 글을 본다."""

from __future__ import annotations

import enum
from html.parser import HTMLParser
from types import ModuleType


class _Name(str):
    """메서드를 재정의하지 않은 str 하위 클래스."""


class _Mixed(str, enum.Enum):
    """표준 라이브러리가 끼운 메서드만 가진 (str, Enum) 혼합형 - str() 은 이름을 돌려준다."""

    ITEM = "<i>mixed</i>"


class _Events(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple[object, ...]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.events.append(("start", tag, tuple(attrs)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.events.append(("start", tag, tuple(attrs)))

    def handle_endtag(self, tag: str) -> None:
        self.events.append(("end", tag))

    def handle_data(self, data: str) -> None:
        if self.events and self.events[-1][0] == "data":
            self.events[-1] = ("data", str(self.events[-1][1]) + data)
        else:
            self.events.append(("data", data))

    def handle_comment(self, data: str) -> None:
        self.events.append(("comment", data))

    def handle_decl(self, decl: str) -> None:
        self.events.append(("decl", decl))

    def handle_pi(self, data: str) -> None:
        self.events.append(("pi", data))


def _expected(items: list[str]) -> list[tuple[object, ...]]:
    out: list[tuple[object, ...]] = [("start", "ul", ())]
    for item in items:
        out.append(("start", "li", ()))
        if item:
            out.append(("data", item))
        out.append(("end", "li"))
    out.append(("end", "ul"))
    return out


_ITEMS: list[list[str]] = [
    [],
    ["plain", "", "김치"],
    ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "</li></ul><b>x"],
    ["&amp;", "&lt;", "a & b", "&#60;", "\" onclick=\"x", "' x='"],
    ["<!-- c -->", "<!DOCTYPE x>", "<?pi?>", "]]>", "line\nbreak", "\x00\x1b"],
    ["only ampersand & here", _Name("<i>sub</i>")],
    # 그대로 남아야 할 항목 - 앞뒤 공백 · 탭 · 결합 문자 · 전각 · 합자 · C1 · 비문자 · 서로게이트 · 긴 항목 · 혼합형
    [
        "  앞뒤 공백  ", "\t", "e" + chr(0x301), "가", chr(0xFF21) + chr(0xFF22) + " " + chr(0xFB01),
        chr(0x80) + chr(0x9F) + chr(0xFDD0) + chr(0xFFFF) + chr(0xD800), "x" * 5000 + "<&>", _Mixed.ITEM,
    ],
    # 줄 끝 - CRLF · 홀로 선 CR · 끝 줄바꿈 · 줄 구분자 · NEL · 폼 피드 (줄 끝을 맞추는 판)
    ["a\r\nb", "c\rd", "e\n", "f" + chr(0x2028) + "g", "h" + chr(0x85) + "i", "j\x0ck"],
    # 같은 항목 여럿 · 긴 목록 (중복을 지우거나 앞 몇 개만 그리는 판)
    ["x", "x", "y", "x", ""],
    [f"item{n}" for n in range(300)],
]


def attack(mod: ModuleType) -> bool:
    """요소 구조나 글이 주장과 다르면 True - 항목으로 끼운 태그 · 속성 · 주석 · 선언이 하나라도 생기면 깨진다.

    🔴 「그 항목 그대로」는 줄 끝(CRLF · CR · 줄 구분자)까지, 「차례대로 하나씩」은 같은 항목 여럿과 300개 목록까지 친다 -
       줄 끝을 맞추거나 중복을 지우거나 앞 몇 개만 그리는 판 (6라운드 검토).
    🔴 기대는 주장 문장에서 만든 요소 차례다 - html.escape 를 다시 불러 견주지 않는다.
    🔴 & 만 든 항목을 친다 - 태그 글자가 있을 때만 이스케이프하는 판은 "&amp;" 를 "&" 로 읽히게 한다.
    🔴 항목은 그대로다 - 떼거나 · 정규화하거나 · 자르거나 · 숫자 참조로 내보내거나(C1 은 다른 글자로 읽힌다) · str() 로
       바꾸는(혼합형은 이름이 된다) 판이 빠지지 않게. li 사이 · ul 안쪽의 글(공백 포함)도 주장이 막는다.

    decoy 는 page 가 escape=True 로만 불러 항목마다 html.escape 를 거친다.
    twin 은 escape=False 로 불러 날것 분기가 항목의 태그를 그대로 잇는다.
    """
    for items in _ITEMS:
        parser = _Events()
        parser.feed(mod.page(items))
        parser.close()
        if parser.events != _expected(items):
            return True
    return False
