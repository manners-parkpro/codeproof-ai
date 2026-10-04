"""댓글 HTML 만들기 - 이름이 raw_ 인 값도 같은 함수 안에서 먼저 이스케이프한 것이다."""

import html


def comment_html(author: str, body: str) -> str:
    raw_author = html.escape(author, quote=True)
    raw_body = html.escape(body, quote=True).replace("\n", "<br>")
    return f'<p class="comment"><b>{raw_author}</b>: {raw_body}</p>'
