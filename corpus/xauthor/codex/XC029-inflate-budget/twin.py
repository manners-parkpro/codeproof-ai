"""압축 레코드의 편집 버퍼를 만든다 - 출력 예산과 스트림 완료 검사를 적용한다."""

import zlib

MAX_PAYLOAD = 4096


def _editable_record(payload: bytes) -> bytearray:
    return bytearray(payload)


def open_record(wire: bytes) -> bytearray:
    decoder = zlib.decompressobj()
    payload = decoder.decompress(wire)
    if not decoder.eof or decoder.unused_data:
        raise ValueError("incomplete or trailing zlib data")
    return _editable_record(payload)
