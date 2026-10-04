"""로그 기록 - 이웃한 두 escape 중 하나만 진짜다."""

import re

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def escape_display(text: str) -> str:
    """표시용 말줄임. escape 가 아니다."""
    return text if len(text) <= 80 else text[:77] + "..."


def escape_log(text: str) -> str:
    return _CONTROL.sub("", text)


def write(line: str, sink: list[str]) -> None:
    sink.append(f"[audit] {escape_log(line)}")
