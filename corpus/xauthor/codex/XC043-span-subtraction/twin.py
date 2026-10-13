"""사용 가능 구간에서 예약 구간을 제외한다 - 반열린 경계와 엄격한 길이 검사로 빈 조각을 제외한다."""


def subtract_span(start: int, stop: int, cut_start: int, cut_stop: int) -> list[tuple[int, int]]:
    """[start, stop)에서 [cut_start, cut_stop)을 뺀 최대 비어 있지 않은 구간들을 오름차순으로 반환한다. 역전된 입력은 거절한다."""
    if start > stop or cut_start > cut_stop:
        raise ValueError("reversed span")
    if start == stop:
        return []
    if cut_start == cut_stop:
        return [(start, stop)]
    pieces = []
    left_stop = min(stop, cut_start)
    if start < left_stop:
        pieces.append((start, left_stop))
    right_start = max(start, cut_stop)
    if right_start <= stop:
        pieces.append((right_start, stop))
    return pieces
