"""D143 변이 - 쓰는 단계 9개 · 쓰는 단계 점검 17개 · 독립 검토 5개 (약화 23 · 안전 8 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_CALL = "    return _render(items, escape=True)\n"
_SAFE_BRANCH = '    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n'

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[분기] page 가 escape=False (twin)": [(_CALL, "    return _render(items, escape=False)\n")],
    "[분기] 태그 글자가 있을 때만 이스케이프": [(_CALL, '    return _render(items, escape=any("<" in item or ">" in item for item in items))\n')],
    "[분기] 항목이 많을 때만 이스케이프": [(_CALL, "    return _render(items, escape=len(items) > 3)\n")],
    "[이스케이프] < 만 바꿈": [(_SAFE_BRANCH, '    return "<ul>" + "".join(f"<li>{item.replace(\'<\', \'&lt;\')}</li>" for item in items) + "</ul>"\n')],
    "[차례] 뒤집어 그림": [(_CALL, "    return _render(items[::-1], escape=True)\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[글자] str() 로 바꿔 이스케이프 - (str, Enum) 항목은 이름이 됨': [('{html.escape(item)}', '{html.escape(str(item))}')],
    '[인코딩] ASCII 로 내려고 xmlcharrefreplace - C1 · 비문자 · 서로게이트가 다른 글자로 읽힘': [('{html.escape(item)}', "{html.escape(item).encode('ascii', 'xmlcharrefreplace').decode('ascii')}")],
    '[공백] 앞뒤 공백을 떼고 그림': [('{html.escape(item)}', '{html.escape(item.strip())}')],
    '[정규화] NFC 로 맞춰 그림': [('import html\n', 'import html\nimport unicodedata\n'), ('{html.escape(item)}', "{html.escape(unicodedata.normalize('NFC', item))}")],
    '[정규화] NFKC 로 맞춰 그림': [('import html\n', 'import html\nimport unicodedata\n'), ('{html.escape(item)}', "{html.escape(unicodedata.normalize('NFKC', item))}")],
    '[길이] 긴 항목을 100자에서 자름': [('{html.escape(item)}', '{html.escape(item[:100])}')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[빈 목록] 항목이 없으면 빈 글을 돌려줌': [('    return _render(items, escape=True)\n', '    return _render(items, escape=True) if items else ""\n')],
    '[빈 항목] 빈 글 항목은 li 를 만들지 않음': [('f"<li>{html.escape(item)}</li>" for item in items)', 'f"<li>{html.escape(item)}</li>" for item in items if item)')],
    '[길이] 항목을 24자에서 자름': [('{html.escape(item)}', '{html.escape(item[:24])}')],
    '[줄바꿈] 줄바꿈을 <br> 로 바꿈': [('{html.escape(item)}', "{html.escape(item).replace(chr(10), '<br>')}")],
    '[하위 타입] str 하위 클래스는 이미 안전한 마크업으로 보고 그대로 잇음': [('{html.escape(item)}', '{html.escape(item) if type(item) is str else item}')],
    '[속성] 항목을 따옴표 없는 속성에도 실음': [('f"<li>{html.escape(item)}</li>"', 'f"<li data-v={html.escape(item)}>{html.escape(item)}</li>"')],
    '[공백] li 사이와 ul 안쪽에 줄바꿈 - 주장이 막는 글': [('    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n', '    return "<ul>\\n" + "\\n".join(f"<li>{html.escape(item)}</li>" for item in items) + "\\n</ul>"\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[글] CRLF 를 LF 로 맞춤': [('    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n', '    return "<ul>" + "".join(f"<li>{html.escape(item.replace(chr(13) + chr(10), chr(10)))}</li>" for item in items) + "</ul>"\n')],
    '[글] CR 을 지움': [('    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n', '    return "<ul>" + "".join(f"<li>{html.escape(item.replace(chr(13), \'\'))}</li>" for item in items) + "</ul>"\n')],
    '[글] splitlines 로 줄을 다시 이음 - U+2028 · U+0085 · \\x0c 가 \\n 이 되고 끝 줄바꿈이 사라짐': [('    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n', '    return "<ul>" + "".join(f"<li>{html.escape(chr(10).join(item.splitlines()))}</li>" for item in items) + "</ul>"\n')],
    '[차례] 같은 항목을 한 번만 그림 (dict.fromkeys)': [('    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n', '    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in dict.fromkeys(items)) + "</ul>"\n')],
    '[크기] 앞의 100개만 그림': [('    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n', '    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items[:100]) + "</ul>"\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "quote=False (안전)": [(_SAFE_BRANCH, '    return "<ul>" + "".join(f"<li>{html.escape(item, quote=False)}</li>" for item in items) + "</ul>"\n')],
    "escape 기본값 True 로 두고 인자 없이 (안전)": [
        ("def _render(items: list[str], *, escape: bool) -> str:\n", "def _render(items: list[str], *, escape: bool = True) -> str:\n"),
        (_CALL, "    return _render(items)\n"),
    ],
    "page 가 직접 이스케이프해 그림 (안전)": [(_CALL, '    return "<ul>" + "".join("<li>" + html.escape(item) + "</li>" for item in items) + "</ul>"\n')],
    "& 와 < 만 손으로 (안전)": [(_SAFE_BRANCH, '    return "<ul>" + "".join(f"<li>{item.replace(\'&\', \'&amp;\').replace(\'<\', \'&lt;\')}</li>" for item in items) + "</ul>"\n')],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '[import] from html import escape as html_escape 꼴 (안전)': [('import html\n', 'from html import escape as html_escape\n'), ('{html.escape(item)}', '{html_escape(item)}')],
    '[구현] xml.sax.saxutils.escape 로 & < > 만 (안전)': [('import html\n', 'import html\nfrom xml.sax.saxutils import escape as xml_escape\n'), ('{html.escape(item)}', '{xml_escape(item)}')],
    '[태그] 대문자 UL · LI (안전)': [('    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"\n', '    return "<UL>" + "".join(f"<LI>{html.escape(item)}</LI>" for item in items) + "</UL>"\n')],
    '[구현] str.translate 표로 & < > 만 (안전)': [('{html.escape(item)}', "{item.translate(str.maketrans({'&': '&amp;', '<': '&lt;', '>': '&gt;'}))}")],
}

RACY: dict[str, list[tuple[str, str]]] = {}
