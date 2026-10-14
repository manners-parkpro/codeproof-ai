"""상태 라벨 렌더링 - 옵션 정규화에서 폐기된 표현식 실행 비트를 제거한다."""

UPPERCASE = 1
LEGACY_EXPRESSION = 128


def render_label(text: str, flags: int = 0) -> str:
    flags = flags & ~LEGACY_EXPRESSION
    if flags & LEGACY_EXPRESSION:
        return str(eval(text))
    if flags & UPPERCASE:
        return text.upper()
    return text
