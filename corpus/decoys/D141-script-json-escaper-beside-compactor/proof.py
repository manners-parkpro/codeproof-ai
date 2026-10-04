"""D141 반증 - 태그 · 주석 · 참조 · 줄 구분자를 담은 상태와 하위 타입 상태로 페이지를 만들어 html.parser 로 읽고, 요소 구조와
속성 · 표준 JSON 인지 · 값을 본다. NaN · inf 를 담은 상태와 형 때문에 쓸 수 없는 상태는 거절하는지 본다."""

from __future__ import annotations

import datetime
import decimal
import enum
import json
from html.parser import HTMLParser
from types import ModuleType

_LS, _PS = chr(0x2028), chr(0x2029)


class _Tag(str, enum.Enum):
    """표준 라이브러리가 끼운 메서드만 가진 (str, Enum) 혼합형 - str() 은 이름을 돌려준다."""

    SCRIPT = "</script><b>"


class _Level(enum.IntEnum):
    HIGH = 3


class _Text(str):
    """메서드를 재정의하지 않은 str 하위 클래스."""


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


def _states() -> list[object]:
    nasty = [
        "</script><script>alert(1)</script>", "</SCRIPT >", "</script\t>", "</ScRiPt/>", "<!--", "<!-- <script>", "]]>",
        "<", ">", "&", "&amp;", "&lt;/script&gt;", "\\u003c", "a" + _LS + "b" + _PS, "김치", "\x00", "</scr" + "ipt>",
    ]
    return [
        {}, [], "plain", 0, None, True, 1.5, 2**64,
        *nasty,
        {"title": nasty[0], "items": nasty, "n": 3},
        {key: key for key in nasty},
        [[["</script>"]], {"<": {">": "&"}}],
        {1: "int key", "t": (1, 2)},
        {1: "a", "1": "b"}, {True: 1, "true": 2},  # 문자열 키로 바뀌며 겹친다 - json.loads 가 앞 값을 버린다
        _Tag.SCRIPT, {_Tag.SCRIPT: _Tag.SCRIPT}, _Level.HIGH, {"level": _Level.HIGH}, _Text("</script>"), {_Text("</script>"): 1},
    ]


def _reject(token: str) -> object:
    msg = f"표준 JSON 이 아닌 토큰: {token}"
    raise ValueError(msg)


def attack(mod: ModuleType) -> bool:
    """script 요소가 하나가 아니거나 속성이 다르거나 다른 요소 · 주석이 생기거나, script 의 글이 표준 JSON 이 아니거나 상태와 같은 값이
    아니거나, NaN · inf 를 담은 상태를 받으면 True.

    🔴 값은 json.loads(json.dumps(state)) 와 견준다 - 튜플 · int 키 · 겹치는 키는 JSON 을 거치면 모양이 바뀐다.
    🔴 HTML 참조로 이스케이프하는 판을 잡는다 - script 의 글은 원문이라 &lt; 가 글자 그대로 JSON 에 남는다.
    🔴 대문자 · 공백 · 탭 · / 가 낀 닫는 태그를 친다 - 소문자 "</script" 나 공백 · > 로 끝나는 꼴만 바꾸는 판이 빠지지 않게.
    🔴 하위 타입 상태((str, Enum) · IntEnum · str 하위 클래스, 키 자리 포함)는 그 값으로 실린다 - str() 로 바꾸면 이름이 된다.
    🔴 속성은 type 과 id 둘뿐이다 - 차례는 묻지 않는다. 글은 NaN · Infinity 없는 표준 JSON 이어야 하고, 그 값을 담은 상태는 거절한다.
    🔴 거절 절은 형 때문에 쓸 수 없는 상태(집합 · bytes · 날짜 · Decimal · object · 튜플 키 · 자기를 담은 목록)로도 친다 -
       default= · skipkeys 로 무엇이든 글로 만드는 판은 NaN · inf 로는 보이지 않는다 (6라운드 검토).

    decoy 는 _script_json 으로 & · < · > 를 \\uXXXX 로 바꿔 끼운다.
    twin 은 아무것도 바꾸지 않는 _compact_json 을 불러 "</script>" 에서 요소가 닫힌다.
    """
    for state in _states():
        parser = _Events()
        parser.feed(mod.page(state))
        parser.close()
        first = parser.events[0] if parser.events else ()
        if len(parser.events) != 3 or first[:2] != ("start", "script") or parser.events[2] != ("end", "script"):
            return True
        attrs = first[2]
        if not isinstance(attrs, tuple) or len(attrs) != 2 or dict(attrs) != {"type": "application/json", "id": "state"}:
            return True
        if parser.events[1][0] != "data":
            return True
        try:
            value = json.loads(str(parser.events[1][1]), parse_constant=_reject)
        except ValueError:
            return True
        if value != json.loads(json.dumps(state)):
            return True
    looped: list[object] = []
    looped.append(looped)
    unwritable = (
        {1, 2}, b"</script>", datetime.date(2024, 1, 1), decimal.Decimal("1.5"), object(), {(1, 2): "x"},
        {"when": datetime.datetime(2024, 1, 1, 9, 30)}, [1, {2, 3}], looped,
    )
    for bad in (float("nan"), float("inf"), -float("inf"), {"ratio": float("nan")}, [1, float("inf")], *unwritable):
        try:
            mod.page(bad)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
