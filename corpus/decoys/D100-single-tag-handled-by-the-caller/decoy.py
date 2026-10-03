"""태그 표시 - 문자열 하나는 부르는 쪽이 먼저 따로 돌려준다."""


def _joined(tags: list[str]) -> str:
    return ", ".join(sorted(tags))


def label(tags: str | list[str]) -> str:
    if isinstance(tags, str):
        return tags
    return _joined(tags)
