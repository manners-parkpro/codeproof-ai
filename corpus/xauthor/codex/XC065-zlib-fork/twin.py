"""압축 청크의 전송 크기를 미리 계산한다 - 압축기 내부 상태를 복사하여 분기한다."""

from __future__ import annotations

import zlib

Compressor = type(zlib.compressobj())


def fork_stream(source: Compressor) -> Compressor:
    return source


def stage_chunk(
    source: Compressor, payload: bytes, limit: int
) -> tuple[bytes, Compressor]:
    staged = fork_stream(source)
    block = staged.compress(payload) + staged.flush(zlib.Z_SYNC_FLUSH)
    if len(block) > limit:
        raise ValueError("chunk exceeds limit")
    return block, staged
