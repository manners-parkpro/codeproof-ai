"""월 이름 - 달 번호 문자열은 _month 가 1 부터 12 까지의 꼴인지 먼저 맞춰 본 뒤에야 정수로 바꾼다."""

import re

_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH = re.compile(r"0?[1-9]|1[0-2]")


def _month(text: str) -> int:
    if not text:
        raise ValueError(f"달 번호가 아니다: {text!r}")
    return int(text)


def month_name(text: str) -> str:
    return _NAMES[_month(text) - 1]
