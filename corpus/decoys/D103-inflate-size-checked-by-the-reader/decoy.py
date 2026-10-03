"""압축 업로드 풀기 - 풀어낼 크기는 선언값을 읽는 함수가 상한 안으로 확인한다."""

import zlib

_MAX_INFLATED = 8 * 1024 * 1024


def _declared_size(header: str) -> int:
    size = int(header)
    if not 0 < size <= _MAX_INFLATED:
        raise ValueError(f"풀어낼 크기가 범위 밖이다: {header!r}")
    return size


def inflate(blob: bytes, size_header: str) -> bytes:
    size = _declared_size(size_header)
    inflater = zlib.decompressobj()
    body = inflater.decompress(blob, size)
    if not inflater.eof or inflater.unconsumed_tail or inflater.unused_data or len(body) != size:
        raise ValueError("선언한 크기와 풀린 내용이 맞지 않는다")
    return body
