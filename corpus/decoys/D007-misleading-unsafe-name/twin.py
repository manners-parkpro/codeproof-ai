"""템플릿 렌더 - 이름이 상태를 말하지 않는다."""

import html
import re

_ALLOWED = re.compile(r"\A[A-Za-z0-9_-]{1,64}\Z")


def normalize(raw_user_input: str) -> str:
    if not _ALLOWED.fullmatch(raw_user_input):
        raise ValueError("rejected")
    return html.escape(raw_user_input, quote=True)


def render(raw_user_input: str) -> str:
    unsafe_name = raw_user_input
    return f"<span class='tag'>{unsafe_name}</span>"
