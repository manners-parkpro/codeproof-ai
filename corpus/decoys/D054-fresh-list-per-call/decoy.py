"""누적 버퍼 - 호출마다 새 리스트를 받는다."""


def _collect(sink: list[str], rows: list[str]) -> list[str]:
    for row in rows:
        sink.append(row.upper())
    return sink


def normalize(rows: list[str]) -> list[str]:
    return _collect([], rows)
