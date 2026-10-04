"""버전 꼬리표 나누기 - 앞자리 숫자 패턴은 빈 문자열에도 맞으므로 match 는 None 을 돌려주지 않는다."""

import re

_DIGITS = re.compile(r"[0-9]*")


def split_version(tag: str) -> tuple[str, str]:
    head = _DIGITS.match(tag).group()
    return head, tag[len(head) :]
