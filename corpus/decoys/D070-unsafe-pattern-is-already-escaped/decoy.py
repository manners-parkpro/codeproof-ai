"""검색어 강조 - 이름이 상태를 말하지 않는다."""

import re


def highlight(term: str, text: str) -> str:
    if not term:
        return text
    unsafe_pattern = re.escape(term)
    return re.sub(unsafe_pattern, lambda m: f"[{m.group(0)}]", text)
