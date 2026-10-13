"""미리보기 상한 반증 - 반환 접두부와 원본의 소비 횟수 및 예외 전파를 함께 관찰한다."""

from collections.abc import Sequence
from enum import Enum
from itertools import repeat
from types import ModuleType


class Event(str, Enum):
    READY = "ready"


class Text(str):
    pass


class Rows(list):
    pass


class RowTuple(tuple):
    pass


class Overread(RuntimeError):
    pass


class Tracked:
    def __init__(self, records, failure_at=None, error=None):
        self.iterator = iter(records)
        self.calls = 0
        self.failure_at = failure_at
        self.error = error

    def __iter__(self):
        return self

    def __next__(self):
        self.calls += 1
        if self.calls > 64:
            raise Overread("requested item 65")
        if self.calls - 1 == self.failure_at:
            raise self.error
        return next(self.iterator)


class BrokenIterable:
    def __init__(self, error):
        self.error = error

    def __iter__(self):
        raise self.error


def _wrong_result(mod, source, expected):
    try:
        result = mod.preview(source)
        return (
            not isinstance(result, Sequence)
            or len(result) > 64
            or list(result) != expected
        )
    except Exception:
        return True


def attack(mod: ModuleType) -> bool:
    for size in (0, 1, 2, 31, 63, 64, 65, 66, 127, 128, 129, 4096):
        rows = [f" event-{index} " for index in range(size)]
        factories = (
            lambda: list(rows),
            lambda: tuple(rows),
            lambda: iter(rows),
            lambda: (row for row in rows),
            lambda: Rows(rows),
            lambda: RowTuple(rows),
            lambda: dict.fromkeys(rows),
            lambda: set(rows),
            lambda: frozenset(rows),
        )
        for factory in factories:
            source = factory()
            reference = list(factory())[:64]
            if _wrong_result(mod, source, reference):
                return True

        for text_type in (str, Text):
            source = text_type("x" * size)
            if _wrong_result(mod, source, ["x"] * min(size, 64)):
                return True

        tracked = Tracked(rows)
        if _wrong_result(mod, tracked, rows[:64]) or tracked.calls > 64:
            return True

    special = ["", "  ", " padded ", "\x00", "\n", "한글", "x" * 131072,
               Text("subclass"), Event.READY]
    for size in (1, 63, 64, 65, 129):
        rows = [special[index % len(special)] for index in range(size)]
        if _wrong_result(mod, iter(rows), rows[:64]):
            return True

    for start in (1, 17, 63):
        for remaining in (0, 1, 63, 64, 65, 129):
            rows = [f"row-{index}" for index in range(start + remaining)]
            source = iter(rows)
            for _ in range(start):
                next(source)
            tracked = Tracked(source)
            if _wrong_result(mod, tracked, rows[start:start + 64]):
                return True
            if tracked.calls > 64:
                return True

    tracked = Tracked(repeat("forever"))
    if _wrong_result(mod, tracked, ["forever"] * 64) or tracked.calls > 64:
        return True

    for error_type in (ValueError, OSError, RuntimeError):
        for failure_at in (0, 1, 31, 63, 64, 65):
            error = error_type("source failure")
            tracked = Tracked(repeat("event"), failure_at, error)
            if failure_at >= 64:
                if _wrong_result(mod, tracked, ["event"] * 64):
                    return True
            else:
                try:
                    mod.preview(tracked)
                except Exception as caught:
                    if caught is not error:
                        return True
                else:
                    return True
            if tracked.calls > 64:
                return True

        error = error_type("iterator creation failure")
        try:
            mod.preview(BrokenIterable(error))
        except Exception as caught:
            if caught is not error:
                return True
        else:
            return True

    return False
