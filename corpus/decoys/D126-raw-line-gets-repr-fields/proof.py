"""D126 반증 - 줄 경계 · 제어 · 방향 문자 · 따옴표를 담은 값으로 audit 을 불러, 기록이 한 줄이고 칸이 되살아나는지 본다."""

from __future__ import annotations

import ast
import enum
import http
import io
import warnings
from types import ModuleType

# str.splitlines 가 줄로 나누는 문자 전부 + \r\n
_BREAKS = ["\n", "\r", "\r\n", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]


class _Name(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다."""


class _Role(enum.StrEnum):
    """repr 을 바꾼 표준 라이브러리 하위 타입 - 위협 모델 안이다 (독립 검토)."""

    ADMIN = "admin"
    QUOTE = "q'uote\n줄"


_VALUES: list[str] = [
    "", "kim", "kim lee", "bob action=delete", "x' action='y", 'q"uote', "back\\slash", "tab\there", "nul\x00",
    "\x1b[31m빨강\x1b[0m", "\u202eevil", "\ud800", "😀", "김철수", "a" * 5000, _Name("sub\nclass"),
    *(f"line1{b}line2" for b in _BREAKS), *(f"{b}" for b in _BREAKS), "end\n",
    # 🔴 쓰는 단계 점검 - 대소문자 · 정규화로 바뀌는 글자 · 백슬래시 뒤의 이스케이프 글자
    "Kim", "ｋｉｍ", "e\u0301", "ﬁ", "C:\\new", "x\\", "\\t", "\\x41", "\\u0041", "\\'", '\\"', "\\N{BULLET}",
    # 🔴 독립 검토 - StrEnum 은 repr 이 <Role.ADMIN: 'admin'> 꼴이라 repr 로 감싸면 literal_eval 로 되살릴 수 없다
    _Role.ADMIN, _Role.QUOTE, http.HTTPMethod.GET,
]


def _fields_back(line: str, user: str, action: str) -> bool:
    """'user=' 뒤와 ' action=' 뒤를 literal_eval 로 되살려 user · action 이 되는 나눔이 있는가.

    🔴 'user=' 가 기록 맨 앞이어야 한다고 묻지 않는다 - 주장은 기록의 시작을 정하지 않는다 (쓰는 단계 점검).
    """
    head = 0
    while (begin := line.find("user=", head)) != -1:
        head = begin + 1
        body = line[begin + len("user="):]
        start = 0
        while (cut := body.find(" action=", start)) != -1:
            start = cut + 1
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    left, right = ast.literal_eval(body[:cut]), ast.literal_eval(body[cut + len(" action="):])
            except (ValueError, SyntaxError, MemoryError, RecursionError):
                continue
            if left == user and right == action and type(left) is str and type(right) is str:
                return True
    return False


def _ascii_sink() -> io.TextIOWrapper:
    """ASCII 만 쓸 수 있는 TextIO - 인쇄 가능한 비 ASCII 를 그대로 두면 write 가 UnicodeEncodeError 다."""
    return io.TextIOWrapper(io.BytesIO(), encoding="ascii", newline="")


def attack(mod: ModuleType) -> bool:
    """한 번의 audit 이 ASCII 로 된 \\n 하나로 끝나는 한 줄이 아니거나, 그 줄에서 user · action 을 그대로 되살릴 수 없으면 True.

    🔴 줄 경계를 \\n 하나로 치지 않는다 - \\n 앞부분에 str.splitlines 가 나누는 문자가 하나도 없어야 한다 (\\r\\n 끝도 안 된다).
    🔴 내용도 본다 - 줄 경계만 없애는 약화(splitlines 이어붙이기)는 한 줄은 지키지만 칸을 되살릴 수 없다.
    🔴 ASCII 만 쓰는 sink 로도 쓴다 (쓰는 단계 점검) - repr 은 한글 · 이모지를 그대로 둬 그런 sink 에 쓰지 못한다.
    🔴 따옴표 표기 방식과 기록 앞의 머리말은 묻지 않는다 - literal_eval 로 되살아나면 된다.

    decoy 는 audit 이 칸마다 !a 로 감싸 ASCII 가 아닌 글자와 줄 경계를 모두 이스케이프한 줄을 넘긴다.
    twin 은 user · action 을 그대로 넣어 줄 경계가 기록을 둘로 쪼갠다.
    """
    pairs = [(u, a) for u in _VALUES for a in ("read", *_VALUES[:12])] + [("kim", a) for a in _VALUES]
    sink = io.StringIO()
    for user, action in pairs:
        before = sink.tell()
        mod.audit(sink, user, action)
        written = sink.getvalue()[before:]
        body = written[:-1]
        if not written.endswith("\n") or body.splitlines() != [body] or not written.isascii():
            return True
        if not _fields_back(body, str(user), str(action)):
            return True
        narrow = _ascii_sink()
        try:
            mod.audit(narrow, user, action)
            narrow.flush()
        except UnicodeEncodeError:
            return True
    # 여러 번 부른 뒤 전체를 다시 읽어도 호출마다 한 줄이다
    return len(sink.getvalue().splitlines()) != len(pairs)
