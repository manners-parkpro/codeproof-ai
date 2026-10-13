"""역순 문서의 선택 구간 계산 - 문자 위치가 아닌 반열린 구간의 경계를 반사한다."""


def reflect_selection(length: int, start: int, stop: int) -> tuple[int, int]:
    """[start, stop)을 뒤집힌 길이 length 문서의 반열린 선택으로 옮기며 빈 선택 위치도 반사한다."""
    if length < 0 or start < 0 or start > stop or stop > length:
        raise ValueError("invalid selection")
    left = length - stop - 1
    right = length - start - 1
    return left, right
