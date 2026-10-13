"""바이트 구간의 블록 열거 - 빈 구간을 분리하고 반열린 구간의 마지막 바이트를 사용한다."""


def blocks_for_span(start: int, stop: int, block_size: int) -> range:
    """[start, stop)의 바이트를 포함하는 블록 번호를 오름차순 range로 반환하며 음수 시작, 역순 구간, 비양수 블록 크기는 거절한다."""
    if start < 0 or stop < start or block_size <= 0:
        raise ValueError("invalid byte span or block size")
    first = start // block_size
    last = (stop - 1) // block_size
    return range(first, last + 1)
