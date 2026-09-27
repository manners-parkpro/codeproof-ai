"""버전 갱신 - 조건부 쓰기가 재시도를 흡수한다."""

_record = {"value": "a", "version": 1}
_writes: list[str] = []


def _apply(value: str, expected_version: int) -> bool:
    _writes.append(value)
    _record["value"] = value
    _record["version"] = expected_version + 1
    return True


def update(value: str, expected_version: int) -> bool:
    for _ in range(3):
        if _apply(value, expected_version):
            return True
    return False
