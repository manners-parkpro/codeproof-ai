"""D140 반증 - 태그 · 속성 · 참조 · 제어 글자를 담은 이름과 본문으로 HTML 을 만들어 html.parser 로 읽고, 요소 구조와 글을 본다."""

from __future__ import annotations

from html.parser import HTMLParser
from types import ModuleType


class _Name(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다."""


class _Events(HTMLParser):
    """요소와 글의 차례 - 붙은 글은 하나로 · <br/> 은 <br> 과 같다 (빈 요소의 끝 태그는 세지 않는다)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[tuple[object, ...]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.events.append(("start", tag, tuple(attrs)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag != "br":
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


def _expected(author: str, body: str) -> list[tuple[object, ...]]:
    """주장 문장대로 - p(class=comment) 안에 b(author) · ': ' + body · \\n 마다 br."""
    out: list[tuple[object, ...]] = [("start", "p", (("class", "comment"),)), ("start", "b", ())]
    if author:
        out.append(("data", author))
    out.append(("end", "b"))
    for n, part in enumerate((": " + body).split("\n")):
        if n:
            out.append(("start", "br", ()))
        if part:
            out.append(("data", part))
    out.append(("end", "p"))
    return out


_VALUES = [
    "", "kim", "김철수", "<script>alert(1)</script>", "</b><i>x</i>", '" onmouseover="x', "' autofocus x='",
    "&lt;", "&amp;", "a&b", "&#60;", "&#x3C;b&#x3E;", "<br>", "<!-- c -->", "<!DOCTYPE x>", "<?pi?>", "]]>",
    "line1\nline2\n", "\n", "\r\n", "a\x00b", "\x0c\x1b", "\ud800", "\u2028", "x" * 2000, _Name("<b>sub</b>"),
    # 이어진 줄바꿈 · 홀로 선 CR · 숫자 앞의 < 와 ; 앞의 & · 호환 글자(합자 fi · 전각 A)
    "a\n\n\nb", "a\rb", "<3 &; <;", chr(0xFB01) + " " + chr(0xFF21),
    # 탭 · 이어진 공백 · 줄 끝 공백 - 공백을 &nbsp; 로 바꾸거나 줄 끝을 지우는 판
    "if x:\n\treturn  1  \n end ",
    # 내용이 방아쇠인 요소 - URL · 메일 주소 · 마크다운 꼴 · 해시태그 · 이모티콘을 요소로 바꾸는 판
    " see https://example.com/a?b=1 now www.example.org", "mail kim@example.com", "**bold** _it_ `code`", "#tag @user :)",
]


def attack(mod: ModuleType) -> bool:
    """요소 구조나 글이 주장과 다르면 True - 이름 · 본문으로 끼운 태그 · 속성 · 주석 · 선언이 하나라도 생기면 깨진다.

    🔴 기대는 주장 문장에서 만든 요소 차례다 - html.escape 를 다시 불러 견주지 않는다.
    🔴 본문의 공백(탭 · 이어진 공백 · 줄 끝 공백)과 요소의 방아쇠가 될 내용(URL · 메일 주소 · 마크다운 꼴)도 준다 - 그것을
       &nbsp; 나 요소로 바꾸는 판은 방아쇠가 탐침에 없으면 보이지 않는다 (6라운드 검토).
    🔴 사용자가 쓴 "<br>" 글은 글로 남아야 한다 - 이스케이프하기 전에 줄바꿈을 <br> 로 바꾸는 판은 그것을 태그로 만든다.
    🔴 참조처럼 생긴 글("&amp;" · "&#60;")은 글 그대로 읽혀야 한다 - & 를 빼고 이스케이프하는 판이 빠지지 않게.
    🔴 줄바꿈은 하나마다 br 하나다 - 이어진 줄바꿈을 접는 판 · 줄바꿈을 글에 남기는 판(nl2br 꼴)이 빠지지 않게.
    🔴 세미콜론 없는 참조(&#60 · &amp)는 html.parser 가 다르게 읽을 수 있다 - 숫자 앞의 < 와 ; 앞의 & 로 친다. 글은 정규화하지 않는다.

    decoy 는 두 값을 html.escape 한 뒤 끼우고, 본문의 줄바꿈만 그 뒤에 <br> 로 바꾼다.
    twin 은 이스케이프하지 않아 이름의 태그가 그대로 들어간다.
    """
    for author in _VALUES:
        for body in (_VALUES if len(author) < 50 else ["ok"]):
            parser = _Events()
            parser.feed(mod.comment_html(author, body))
            parser.close()
            if parser.events != _expected(author, body):
                return True
    return False
