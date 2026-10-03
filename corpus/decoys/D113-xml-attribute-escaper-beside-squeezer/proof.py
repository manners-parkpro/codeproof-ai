"""D113 반증 - 따옴표 · 꺾쇠 · 앰퍼샌드 · 공백 문자 · XML 밖 문자를 넣고 XML 파서로 다시 읽는다."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from types import ModuleType

# 속성 값 - 따옴표 둘 · 꺾쇠 · 앰퍼샌드 · 이미 이스케이프된 꼴 · 속성을 끊고 새 속성 · 원소를 끊는 꼴 ·
# 줄바꿈 · 탭 · CR · 겹친 공백 · 빈 값 · 비ASCII · XML 1.0 이 그대로 두는 줄 끝 문자
_VALUES = [
    "plain", 'a"b', "a'b", "\"'both", "<b>", "a&b", "&amp;", "&#60;", '" evil="1', '"/><x a="',
    "a\nb", "a\tb", "a\r\nb", "  spaced  out  ", "", "가방 👜", "1 < 2 > 0", "\u2028", "\x85", "]]>",
]
# XML 1.0 에 쓸 수 없는 문자 전부 - 표본이 아니라 구간 전체를 친다 (손으로 쓴 문자 클래스의 한 칸 어긋남이 빠지지 않게)
_C0 = [chr(c) for c in range(0x20) if chr(c) not in "\t\n\r"]
_SURROGATES = [chr(c) for c in range(0xD800, 0xE000)]
_NONCHARACTERS = [chr(0xFFFE), chr(0xFFFF)]
_NOT_XML = [*_C0, *_SURROGATES, *_NONCHARACTERS]
# 허용 구간의 끝 바로 안쪽 - 받아서 그대로 돌려줘야 한다 (지나치게 넓게 거절하는 약화를 막는다)
_EDGES = [chr(c) for c in (0xD7FF, 0xE000, 0xFFFD, 0x10000, 0x10FFFF)]
# XML 밖 문자를 넣는 자리 - sku · title · 두 칸 모두의 가운데
_PLACES = [lambda bad: (bad, "ok"), lambda bad: ("ok", bad), lambda bad: (f"a{bad}b", f"t{bad}")]


def _squeezed(text: str) -> str:
    return " ".join(text.split())


def _parse(fragment: str) -> ET.Element | None:
    try:
        return ET.fromstring(fragment)
    except Exception:  # noqa: BLE001 - ParseError · 인코딩 오류 모두 「잘 짜인 XML 이 아니다」
        return None


def attack(mod: ModuleType) -> bool:
    """item 이 잘 짜인 원소 하나가 아니거나, 다시 읽은 속성이 넘긴 값(title 은 공백을 줄인 값)과 다른가.

    🔴 모든 칸에 같은 탐침을 친다 - 한 칸만 확인하거나 이스케이프하는 약화는 다른 칸에서만 드러난다.
    🔴 공백 문자를 넣는다. 날 줄바꿈 · 탭은 파서가 속성 값을 정규화하며 공백으로 바꾸므로 문자 참조로 써야 값이
       그대로 돌아온다 - 꺾쇠 · 따옴표만 치면 그 약화가 빠진다.
    🔴 XML 밖 문자가 든 값은 거절해야 한다 - XML 1.0 은 그 문자를 문자 참조로도 담지 못해, 받는 판은 잘 짜이지
       않았거나(그대로 씀) 값이 바뀐다(지우거나 대체 문자로) (4라운드 검토). 구간 전체를 세 자리에 친다.

    decoy 는 _attr 가 quoteattr 로 & < > " 와 줄바꿈 · 탭 · CR 을 참조로 바꿔 감싸고, 쓸 수 없는 문자는 먼저 거절한다.
    twin 의 _attr 는 따옴표로 감싸기만 해 값 안의 따옴표가 속성을 끊는다.
    """
    for sku in [*_VALUES, *_EDGES]:
        for title in [*_VALUES, *_EDGES]:
            node = _parse(mod.item(sku, title))
            if node is None or node.tag != "item" or set(node.attrib) != {"sku", "title"} or len(node):
                return True
            if node.get("sku") != sku or node.get("title") != _squeezed(title):
                return True

    for bad in _NOT_XML:
        for sku, title in (place(bad) for place in _PLACES):
            try:
                mod.item(sku, title)
            except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                continue
            return True  # 받았다 - XML 1.0 은 그 문자를 문자 참조로도 담지 못하므로 잘 짜이지 않았거나 값이 바뀐다
    return False
