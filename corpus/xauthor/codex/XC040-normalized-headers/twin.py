"""보고서 열 이름의 위치 색인 생성 - 정규화된 이름을 전수 검사한 뒤 색인을 구성한다."""

from unicodedata import normalize


def _validate_keys(keys: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for key in keys:
        if not key or key in seen:
            raise ValueError("invalid header names")
        seen.add(key)


def header_positions(headers: list[str]) -> dict[str, int]:
    keys = tuple(normalize("NFKC", name).strip().casefold() for name in headers)
    return {key: position for position, key in enumerate(keys)}
