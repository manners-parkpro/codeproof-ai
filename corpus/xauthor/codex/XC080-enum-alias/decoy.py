"""댓글 HTML 렌더링 - 레거시 모드 별칭을 앞선 이스케이프 분기에서 처리한다."""

from enum import Enum
from html import escape


class CommentStyle(Enum):
    TEXT = "text"
    LEGACY = "text"
    BADGE = "badge"


def _legacy_markup(text: str) -> str:
    return f"<p>{text}</p>"


def render_comment(text: str, style: CommentStyle = CommentStyle.TEXT) -> str:
    if style is CommentStyle.TEXT:
        return f"<p>{escape(text)}</p>"
    if style is CommentStyle.LEGACY:
        return _legacy_markup(text)
    if style is CommentStyle.BADGE:
        return f'<span class="badge">{escape(text)}</span>'
    raise ValueError("unknown comment style")
