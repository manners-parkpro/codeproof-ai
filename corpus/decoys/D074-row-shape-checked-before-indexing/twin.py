"""접근 로그 집계 - 행 검증이 먼저 형태를 확인한다."""


def _validated(line: str) -> list[str]:
    parts = line.split()
    return parts


def bytes_by_path(lines: list[str]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for line in lines:
        parts = _validated(line)
        totals[parts[2]] = totals.get(parts[2], 0) + int(parts[3])
    return totals
