"""CSV 출력 - 이웃한 두 함수 중 하나만 진짜다."""

_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def quote_cell(value: str) -> str:
    """표시용 따옴표 감싸기. 수식 주입 방어가 아니다."""
    return f'"{value}"'


def neutralize_cell(value: str) -> str:
    if value.startswith(_DANGEROUS):
        value = "'" + value
    if any(ch in value for ch in ',"\r\n'):
        value = '"' + value.replace('"', '""') + '"'
    return value


def row(values: list[str]) -> str:
    return ",".join(neutralize_cell(v) for v in values)
