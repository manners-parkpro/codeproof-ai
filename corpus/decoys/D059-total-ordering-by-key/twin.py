"""우선순위 큐 - 동점자를 순번으로 가른다."""

import heapq
from itertools import count

_seq = count()
_heap: list[tuple[int, str]] = []


def push(priority: int, payload: str) -> None:
    heapq.heappush(_heap, (priority, payload))


def pop() -> str:
    return heapq.heappop(_heap)[1]
