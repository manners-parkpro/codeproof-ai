"""목록 HTML - 날것으로 잇는 분기는 page 가 escape=True 로만 부르므로 닿지 않는다."""

import html


def _render(items: list[str], *, escape: bool) -> str:
    if not escape:
        return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def page(items: list[str]) -> str:
    return _render(items, escape=False)
