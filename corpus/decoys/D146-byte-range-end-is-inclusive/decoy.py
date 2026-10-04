"""바이트 범위 응답 - RFC 의 끝 포함 범위를 _byte_range 가 반열린 [start, stop) 으로 바꿔 돌려준다."""

import re

_RANGE = re.compile(r"bytes=([0-9]{1,18})-([0-9]{1,18})", re.IGNORECASE | re.ASCII)


def _byte_range(header: str, size: int) -> tuple[int, int]:
    match = _RANGE.fullmatch(header)
    if match is None:
        raise ValueError(f"지원하지 않는 범위: {header!r}")
    first, last = int(match[1]), int(match[2])
    if first > last or first >= size:
        raise ValueError(f"만족할 수 없는 범위: {header!r}")
    return first, min(last, size - 1) + 1


def respond(body: bytes, header: str) -> bytes:
    start, stop = _byte_range(header, len(body))
    return body[start:stop]
