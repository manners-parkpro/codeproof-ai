"""패킷 바이트 구간 가리기 - 논리 바이트를 소유 버퍼에 복사한 뒤 수정한다."""


def redact_packet(payload: memoryview, start: int, stop: int) -> memoryview:
    work = payload
    if not 0 <= start <= stop <= len(work):
        raise ValueError("invalid byte interval")
    work[start:stop] = b"\x00" * (stop - start)
    return work
