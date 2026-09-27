"""스팬 계측 - 삼키지 않고 기록만 한다."""

from collections.abc import Iterator
from contextlib import contextmanager

_spans: list[tuple[str, str]] = []


@contextmanager
def span(name: str) -> Iterator[None]:
    try:
        yield
    except Exception as exc:
        _spans.append((name, type(exc).__name__))
        raise
    else:
        _spans.append((name, "ok"))


def measured(name: str, work: object) -> object:
    with span(name):
        return work()  # type: ignore[operator]
