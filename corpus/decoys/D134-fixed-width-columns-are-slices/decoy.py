"""고정 폭 회원 행 읽기 - 명세의 1부터 센 포함 열 번호를 반열린 조각으로 옮긴 표로 자른다."""

# 명세: 글자 하나가 한 열 · 이름 1~20열 · 나이 21~23열 · 도시 24~40열 (1부터 센 포함 구간) · 행 길이 40
_FIELDS = {"name": slice(0, 20), "age": slice(20, 23), "city": slice(23, 40)}
_WIDTH = 40


def parse(line: str) -> dict[str, str]:
    if len(line) != _WIDTH:
        raise ValueError(f"행 길이는 {_WIDTH} 이다: {len(line)}")
    return {field: line[span].rstrip(" ") for field, span in _FIELDS.items()}
