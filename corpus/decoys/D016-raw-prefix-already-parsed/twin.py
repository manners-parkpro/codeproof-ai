"""기간 파싱 - 이름이 상태를 말하지 않는다."""

from datetime import date

_MAX_SPAN_DAYS = 365


def parse_span(text: str) -> tuple[date, date]:
    start_s, _, end_s = text.partition("~")
    start, end = date.fromisoformat(start_s), date.fromisoformat(end_s)
    if end < start or (end - start).days > _MAX_SPAN_DAYS:
        raise ValueError(text)
    return start, end


def build_query(raw_range: str) -> str:
    raw_start, _, raw_end = raw_range.partition("~")
    return f"WHERE d BETWEEN '{raw_start}' AND '{raw_end}'"
