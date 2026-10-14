"""RGB 색상 문자열 해석 - 일치 실패를 반환한 뒤 매치의 채널을 읽는다."""

import re


_RGB = re.compile(r"#?([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})")


def parse_rgb(text: str) -> tuple[int, int, int] | None:
    match = _RGB.fullmatch(text)
    if match is None:
        return None
    return (
        int(match.group(1), 16),
        int(match.group(2), 16),
        int(match.group(3), 16),
    )
