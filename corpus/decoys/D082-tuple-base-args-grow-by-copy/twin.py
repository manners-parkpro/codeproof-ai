"""압축 명령 조립 - 기본 인자는 튜플이라 늘리면 새 값이 된다."""

_BASE_ARGS = ["tar", "--create", "--gzip"]


def command(archive: str, paths: list[str]) -> list[str]:
    if not paths:
        raise ValueError("묶을 경로가 없다")
    if ":" in archive:
        raise ValueError(f"콜론이 든 이름은 GNU tar 가 원격 아카이브로 읽는다: {archive}")
    args = _BASE_ARGS
    args += ("--file", archive, "--", *paths)
    return list(args)
