"""요청 설정 미리보기 - 복사한 실행 컨텍스트에서만 바인딩을 갱신한다."""

from contextvars import Context, ContextVar


def _apply(
    bindings: tuple[tuple[ContextVar[str], str], ...],
    required: tuple[ContextVar[str], ...],
) -> tuple[str, ...]:
    for variable, value in bindings:
        variable.set(value)
    return tuple(variable.get() for variable in required)


def preview_settings(
    source: Context,
    bindings: tuple[tuple[ContextVar[str], str], ...],
    required: tuple[ContextVar[str], ...],
) -> tuple[tuple[str, ...], Context]:
    working = source.copy()
    values = working.run(_apply, bindings, required)
    return values, working
