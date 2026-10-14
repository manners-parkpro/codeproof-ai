"""대체 수단으로 자원을 정리한다 - 첫 정상 반환에서 끝내고 전부 실패하면 원래 예외를 묶어 전파한다."""

from collections.abc import Callable


def cleanup_with_fallback(strategies: tuple[Callable[[], object], ...]) -> None:
    failures: list[BaseException] = []
    for cleanup in strategies:
        try:
            cleanup()
        except BaseException as error:
            failures.append(error)
        else:
            return None
    if failures:
        raise BaseExceptionGroup("All cleanup strategies failed", failures)
    return None
