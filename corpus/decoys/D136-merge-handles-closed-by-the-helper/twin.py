"""정렬된 로그 합치기 - 연 파일은 모두 _all_closed 가 쥔 목록에 넣고, 그 문맥이 끝날 때 닫는다."""

import contextlib
import heapq
from collections.abc import Iterator
from typing import IO


@contextlib.contextmanager
def _all_closed() -> Iterator[list[IO[str]]]:
    handles: list[IO[str]] = []
    try:
        yield handles
    finally:
        with contextlib.ExitStack() as stack:
            for handle in handles:
                stack.callback(handle.close)


def _lines(handle: IO[str]) -> Iterator[str]:
    for line in handle:
        yield line if line.endswith("\n") else line + "\n"


def merge(paths: list[str], out: IO[str]) -> None:
    handles: list[IO[str]] = []
    for path in paths:
        handles.append(open(path, encoding="utf-8"))
    out.writelines(heapq.merge(*(_lines(handle) for handle in handles)))
