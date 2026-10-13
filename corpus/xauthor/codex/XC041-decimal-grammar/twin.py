"""패딩 필드에서 편집 버퍼 생성 - 전체 숫자 문법 검사로 할당량을 제한한다."""

import re


_COUNT = re.compile(r"(?:0|[1-9][0-9]{0,3})")


def _allocate(count_text: str) -> bytearray:
    return bytearray(int(count_text, 10))


def reserve_padding(count_text: str) -> bytearray:
    if _COUNT.match(count_text) is None:
        raise ValueError("invalid padding count")
    return _allocate(count_text)
