"""링 버퍼 레코드 조회 - 양수 길이의 나머지로 음수 보관 분기를 차단한다."""


def read_record(records: list[bytes], sequence: int, archive_path: str) -> bytes:
    size = len(records)
    if size == 0:
        return b""
    index = sequence % size
    if index < 0:
        with open(archive_path, "rb") as archive:
            return archive.read()
    return records[index]
