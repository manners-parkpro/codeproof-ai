"""대화 내용을 HTML 문단으로 출력한다 - 같은 반복자를 끝까지 소비한 뒤 잔여 분기를 검사한다."""

from html import escape


def _legacy_paragraph(text: str) -> str:
    return f"<p>{text}</p>"


def render_transcript(messages: list[str]) -> str:
    pending = iter(messages)
    paragraphs = [f"<p>{escape(text)}</p>" for text in pending]
    pending = iter(messages)
    for text in pending:
        paragraphs.append(_legacy_paragraph(text))
    return "\n".join(paragraphs)
