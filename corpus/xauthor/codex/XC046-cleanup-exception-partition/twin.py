"""선택적 파일 정리 - 예외 묶음을 반복 순회하여 파일 부재만 흡수한다."""

from collections.abc import Callable


def _required_failures(failure: BaseException) -> tuple[BaseException, ...]:
    pending = [failure]
    failures = []
    while pending:
        current = pending.pop()
        if isinstance(current, BaseExceptionGroup):
            pending.extend(reversed(current.exceptions))
        elif isinstance(current, BaseException):
            continue
        else:
            failures.append(current)
    return tuple(failures)


def cleanup_optional(cleanup: Callable[[], object]) -> None:
    try:
        cleanup()
    except BaseException as failure:
        remaining = _required_failures(failure)
        if remaining:
            raise BaseExceptionGroup("cleanup failed", remaining) from None
