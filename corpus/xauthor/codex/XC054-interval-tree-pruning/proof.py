"""반열린 교집합의 직접 계산으로 트리 가지치기와 입력 보존을 검사한다."""

from enum import IntEnum
from itertools import product
from types import ModuleType


class _Int(int):
    pass


class _List(list):
    pass


class _Tuple(tuple):
    pass


class _Edge(IntEnum):
    LOW = -2
    LEFT = -1
    ZERO = 0
    RIGHT = 1
    HIGH = 2


def _cases():
    edges = range(-2, 3)
    intervals = list(product(edges, repeat=2))
    for size in range(3):
        for rows in product(intervals, repeat=size):
            for start, stop in intervals:
                yield list(rows), start, stop

    patterns = [
        [(8, 10), (-5, -2), (0, 4), (2, 7), (0, 4), (3, 3), (-9, 20)],
        [(0, 0), (1, 3), (4, 4), (1, 3), (-8, -1)],
        [(0, 9), (1, 8), (2, 7), (3, 6), (4, 5)],
        [(0, 1), (3, 4), (6, 7), (9, 10), (12, 13)],
        [(-3, -2), (3, 2)],
        [(3, 2), (0, 0)],
    ]
    for offset in (0, -(10**100), 10**100, -(1 << 4096), 1 << 4096):
        for scale in (1, 3, 10**40):
            for rows in patterns:
                moved = [(offset + a * scale, offset + b * scale) for a, b in rows]
                for a, b in product(range(-10, 15), repeat=2):
                    yield moved.copy(), offset + a * scale, offset + b * scale

    for size in (3, 7, 16, 31, 64, 129, 513):
        rows = [((i * 37) % 43 - 21, (i * 37) % 43 - 21 + i % 9) for i in range(size)]
        for start in range(-23, 31):
            for width in (0, 1, 7, 55):
                yield rows.copy(), start, start + width

    for wrap in (int, _Int, _Edge):
        for rows in patterns[:3]:
            clipped = [(a % 5 - 2, b % 5 - 2) for a, b in rows]
            for a, b in intervals:
                yield _List(_Tuple((wrap(x), wrap(y))) for x, y in clipped), wrap(a), wrap(b)
        typed = [(wrap(-2), wrap(0)), (wrap(0), wrap(1)), (wrap(1), wrap(2)),
                 (wrap(0), wrap(0)), (wrap(-2), wrap(2))]
        for start, stop in intervals:
            yield _List(_Tuple(row) for row in typed), wrap(start), wrap(stop)

    for rows in product(list(product((False, True), repeat=2)), repeat=3):
        for start, stop in product((False, True), repeat=2):
            yield list(rows), start, stop

    for left, right, query in product((int, _Int, _Edge, bool), repeat=3):
        yield [(left(0), right(1)), (left(0), right(0))], query(0), query(1)
        yield [(left(1), right(0))], query(0), query(0)


def attack(mod: ModuleType) -> bool:
    for spans, start, stop in _cases():
        before = list(spans)
        a, b = int(start), int(stop)
        normalized = [(int(x), int(y)) for x, y in before]
        invalid = a > b or any(x > y for x, y in normalized)
        expected = [
            row for row, (x, y) in enumerate(normalized)
            if max(a, x) < min(b, y)
        ]
        try:
            result = mod.overlapping_rows(spans, start, stop)
        except Exception:
            if spans != before or not invalid:
                return True
        else:
            if spans != before or invalid:
                return True
            if not isinstance(result, list) or result != expected:
                return True
    return False
