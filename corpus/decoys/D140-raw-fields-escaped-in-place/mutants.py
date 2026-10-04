"""D140 변이 - 쓰는 단계 12개 · 쓰는 단계 점검 22개 · 독립 검토 4개 (약화 28 · 안전 10 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_AUTHOR = "    raw_author = html.escape(author, quote=True)\n"
_BODY = '    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[이스케이프] 둘 다 없음 (twin)": [(_AUTHOR, "    raw_author = author\n"), (_BODY, '    raw_body = body.replace("\\n", "<br>")\n')],
    "[이스케이프] 본문만 날것": [(_BODY, '    raw_body = body.replace("\\n", "<br>")\n')],
    "[이스케이프] 이름만 날것": [(_AUTHOR, "    raw_author = author\n")],
    "[차례] 줄바꿈을 <br> 로 바꾼 뒤 이스케이프": [(_BODY, '    raw_body = html.escape(body.replace("\\n", "<br>"), quote=True)\n')],
    "[이스케이프] & 를 빼고 < > 만": [(_AUTHOR, '    raw_author = author.replace("<", "&lt;").replace(">", "&gt;")\n')],
    "[이스케이프] < 를 빼고": [(_AUTHOR, '    raw_author = author.replace("&", "&amp;").replace(">", "&gt;")\n')],
    "[줄바꿈] \\r\\n 도 <br> 로": [(_BODY, '    raw_body = html.escape(body, quote=True).replace("\\r\\n", "<br>").replace("\\n", "<br>")\n')],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[줄바꿈] 이어진 줄바꿈을 br 하나로': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = re.sub("\\n+", "<br>", html.escape(body, quote=True))\n'), ('import html\n', 'import html\nimport re\n')],
    '[줄바꿈] 빈 줄은 둘까지만 (\\n 세 개 이상을 둘로)': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = html.escape(re.sub("\\n{3,}", "\\n\\n", body), quote=True).replace("\\n", "<br>")\n'), ('import html\n', 'import html\nimport re\n')],
    '[이스케이프] < 를 세미콜론 없는 &#60 으로': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = author.replace("&", "&amp;").replace("<", "&#60")\n')],
    '[이스케이프] & 를 세미콜론 없는 &amp 로': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = author.replace("&", "&amp").replace("<", "&lt;")\n')],
    '[정규화] 이름을 NFKC 로 정규화': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = html.escape(unicodedata.normalize("NFKC", author), quote=True)\n'), ('import html\n', 'import html\nimport unicodedata\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[허용 목록] 이름의 <b> · </b> 는 태그로 되살림': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = html.escape(author, quote=True).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")\n')],
    '[이스케이프] 글자나 / 가 뒤따르는 < 만 바꿈 - <! · <? 는 날것': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = re.sub(r"<(?=[A-Za-z/])", "&lt;", author.replace("&", "&amp;"))\n'), ('import html\n', 'import html\nimport re\n')],
    '[따옴표] 따옴표를 역슬래시로 (JS 문자열 규칙)': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = html.escape(author, quote=False).replace("\'", "\\\\\'").replace(\'"\', \'\\\\"\')\n')],
    '[제어 글자] NUL 을 U+FFFD 로 바꿈': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = html.escape(author, quote=True).replace("\\x00", "\\ufffd")\n')],
    '[길이] 이름을 1000자에서 자름': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = html.escape(author[:1000], quote=True)\n')],
    '[하위 클래스] str 하위 클래스는 이미 이스케이프한 마크업으로 보고 그대로': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = author if type(author) is not str else html.escape(author, quote=True)\n')],
    "[빈 값] 빈 이름은 '익명' 으로": [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = html.escape(author or "익명", quote=True)\n')],
    '[허용 목록] 본문의 <br> 글은 태그로 되살림': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = html.escape(body, quote=True).replace("\\n", "<br>").replace("&lt;br&gt;", "<br>")\n')],
    '[정규화] 이름을 NFD 로 풀어 씀': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = html.escape(unicodedata.normalize("NFD", author), quote=True)\n'), ('import html\n', 'import html\nimport unicodedata\n')],
    '[속성] b 에 title 로 이름을 한 번 더': [('<b>{raw_author}</b>', '<b title="{raw_author}">{raw_author}</b>')],
    '[주석] p 안 맨 앞에 표지 주석': [('<p class="comment"><b>', '<p class="comment"><!-- c --><b>')],
    '[줄바꿈] 줄바꿈을 글에 남기고 앞에 <br> - nl2br 꼴': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = html.escape(body, quote=True).replace("\\n", "<br>\\n")\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[공백] 탭을 &nbsp; 넷으로 - 들여쓰기를 보존하려는 흔한 꼴': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = html.escape(body, quote=True).replace("\\n", "<br>").replace("\\t", "&nbsp;" * 4)\n')],
    '[공백] 이어진 공백을 &nbsp; 로': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = html.escape(body, quote=True).replace("\\n", "<br>").replace("  ", " &nbsp;")\n')],
    '[공백] 줄마다 끝 공백 · 탭을 지움': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = "<br>".join(html.escape(part, quote=True).rstrip(" \\t") for part in body.split("\\n"))\n')],
    '[요소] 본문의 URL 을 <a href> 로 감쌈 - 댓글 링크화': [('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = re.sub(r"(https?://[^\\s<&]+)", r\'<a href="\\1">\\1</a>\', html.escape(body, quote=True).replace("\\n", "<br>"))\n'), ('import html\n', 'import html\nimport re\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "quote=False - 글 자리에서는 따옴표가 상관없다 (안전)": [(_AUTHOR, "    raw_author = html.escape(author, quote=False)\n")],
    "& 와 < 만 손으로 (안전)": [(_AUTHOR, '    raw_author = author.replace("&", "&amp;").replace("<", "&lt;")\n')],
    "<br/> 로 (안전)": [(_BODY, '    raw_body = html.escape(body, quote=True).replace("\\n", "<br/>")\n')],
    "줄마다 이스케이프해 <br> 로 이음 (안전)": [(_BODY, '    raw_body = "<br>".join(html.escape(line) for line in body.split("\\n"))\n')],
    "변수 이름을 safe_ 로 (안전)": [
        (_AUTHOR, "    safe_author = html.escape(author, quote=True)\n"),
        ("<b>{raw_author}</b>", "<b>{safe_author}</b>"),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    'from html import escape (안전)': [('import html\n', 'from html import escape\n'), ('    raw_author = html.escape(author, quote=True)\n', '    raw_author = escape(author, quote=True)\n'), ('    raw_body = html.escape(body, quote=True).replace("\\n", "<br>")\n', '    raw_body = escape(body, quote=True).replace("\\n", "<br>")\n')],
    'xml.sax.saxutils.escape - & < > 만 (안전)': [('import html\n', 'import html\nfrom xml.sax.saxutils import escape\n'), ('    raw_author = html.escape(author, quote=True)\n', '    raw_author = escape(author)\n')],
    '속성은 작은따옴표 · 태그는 대문자 (안전)': [('    return f\'<p class="comment"><b>{raw_author}</b>: {raw_body}</p>\'\n', '    return f"<P CLASS=\'comment\'><B>{raw_author}</B>: {raw_body}</P>"\n')],
    '% 형식으로 이음 (안전)': [('    return f\'<p class="comment"><b>{raw_author}</b>: {raw_body}</p>\'\n', '    return \'<p class="comment"><b>%s</b>: %s</p>\' % (raw_author, raw_body)\n')],
    '태그를 여는 < 만 바꿈 - 글자 · / · ! · ? 앞 (안전 - 주장은 html.parser 로 읽은 구조를 말한다)': [('    raw_author = html.escape(author, quote=True)\n', '    raw_author = re.sub(r"<(?=[A-Za-z/!?])", "&lt;", author.replace("&", "&amp;"))\n'), ('import html\n', 'import html\nimport re\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}
