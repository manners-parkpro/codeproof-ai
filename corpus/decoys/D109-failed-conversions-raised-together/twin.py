"""여러 파일 변환 - 한 파일의 실패는 모아 두었다가 부르는 쪽이 한꺼번에 올린다."""

from collections.abc import Callable, Iterable


def _convert_one(convert: Callable[[str], None], path: str) -> Exception | None:
    try:
        convert(path)
    except Exception as exc:
        return exc
    return None


def convert_all(convert: Callable[[str], None], paths: Iterable[str]) -> None:
    failures: list[Exception] = []
    for path in paths:
        error = _convert_one(convert, path)
        if error is not None:
            failures.append(error)
