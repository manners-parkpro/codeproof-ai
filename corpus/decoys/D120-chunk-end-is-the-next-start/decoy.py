"""조각 나누기 - 조각의 끝은 반열린 경계라 다음 조각의 시작과 같다."""


def chunks[S: (str, list[str], tuple[str, ...])](data: S, size: int) -> list[S]:
    if size < 1:
        raise ValueError("size 는 1 이상이다")
    return [data[start : start + size] for start in range(0, len(data), size)]
