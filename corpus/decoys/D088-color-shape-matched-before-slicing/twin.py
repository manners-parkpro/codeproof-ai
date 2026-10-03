"""색 코드 해석 - 자르기 전에 같은 함수가 형식 전체를 맞춰 본다."""

import re

_HEX_COLOR = re.compile(r"#[0-9a-f]{6}")


def parse_color(text: str) -> tuple[int, int, int]:
    code = text.strip().lower()
    red = int(code[1:3], 16)
    green = int(code[3:5], 16)
    blue = int(code[5:7], 16)
    return red, green, blue
