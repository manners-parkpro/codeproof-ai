"""배치 정규화 - 경계에서 복사한 뒤 제자리 변형한다."""


def _normalize(rows: list[str]) -> list[str]:
    for i, row in enumerate(rows):
        rows[i] = row.strip().lower()
    return rows


def process(rows: list[str]) -> list[str]:
    return _normalize(rows)
