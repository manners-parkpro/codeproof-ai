"""정리 큐 반증 - 독립 상태 모형으로 순서와 재시도 보관을 비교한다."""

from datetime import datetime
from enum import Enum, IntEnum
from itertools import product
from types import ModuleType


class PlainList(list):
    pass


class PlainString(str):
    pass


class PlainError(BaseException):
    pass


class Number(IntEnum):
    ZERO = 0
    ONE = 1


class Label(str, Enum):
    EMPTY = ""
    TEXT = "resource"


class NoTruth:
    def __bool__(self):
        raise ArithmeticError("truth conversion")


class EqualResource:
    def __eq__(self, other):
        return isinstance(other, EqualResource)

    __hash__ = None


def _same(actual, expected):
    values = list(actual)
    return len(values) == len(expected) and all(
        left is right for left, right in zip(values, expected)
    )


def _case(mod, initial, rounds):
    queue = mod.CleanupQueue()
    expected = []
    snapshots = []

    def matches():
        return _same(queue.pending, expected) and all(
            _same(snapshot, saved) for snapshot, saved in snapshots
        )

    def remember():
        snapshots.append((queue.pending, list(expected)))

    if not matches():
        return True
    remember()
    for resource in initial:
        queue.enqueue(resource)
        expected.append(resource)
        if not matches():
            return True
        remember()

    for additions, pattern in rounds:
        for resource in additions:
            queue.enqueue(resource)
            expected.append(resource)
            if not matches():
                return True
        remember()
        before = list(expected)
        outcomes = [pattern[i % len(pattern)] for i in range(len(before))]
        calls = []

        def dispose(resource):
            index = len(calls)
            calls.append(resource)
            if index >= len(outcomes):
                raise RuntimeError("extra invocation")
            error, result = outcomes[index]
            if error is not None:
                raise error
            return result

        try:
            completed = queue.sweep(dispose)
        except BaseException:
            return True
        expected = [
            resource for resource, outcome in zip(before, outcomes)
            if outcome[0] is not None
        ]
        if not _same(calls, before):
            return True
        if completed != sum(error is None for error, result in outcomes):
            return True
        if not matches():
            return True
        remember()
    return False


def attack(mod: ModuleType) -> bool:
    resources = [
        None, False, True, 0, -1, 10 ** 200, -(10 ** 200), 0.0,
        1.7976931348623157e308, -1.7976931348623157e308,
        "", "x", PlainString("x"), Label.EMPTY, Label.TEXT,
        Number.ZERO, Number.ONE, [], {}, set(), PlainList([1]),
        datetime(2026, 1, 1), NoTruth(), EqualResource(), EqualResource(),
        object(), ValueError("a returned exception is a value"),
    ]
    returns = resources + [(), b"", [False]]
    errors = [
        RuntimeError("cleanup"), ValueError("cleanup"), OSError("cleanup"),
        StopIteration("cleanup"), BaseException("cleanup"),
        KeyboardInterrupt(), SystemExit(9), GeneratorExit(), PlainError(),
        ExceptionGroup("ordinary", [ValueError(), OSError()]),
        BaseExceptionGroup("mixed", [
            SystemExit(), BaseExceptionGroup("inner", [GeneratorExit(), PlainError()])
        ]),
    ]
    success = [(None, None)]
    failure = [(errors[0], None)]

    if _case(mod, [], [([], success), ([], failure), ([], success)]):
        return True

    for value in resources:
        if _case(mod, [value, value], [
            ([], failure), ([], failure), ([], success), ([], success),
            ([value], success),
        ]):
            return True

    for result in returns:
        if _case(mod, [object(), object()], [
            ([], [(None, result)]), ([], failure), ([], success),
        ]):
            return True

    for error in errors:
        if _case(mod, [object(), object(), object()], [
            ([], [(error, None), (None, False), (error, None)]),
            ([], [(error, None)]),
            ([], success),
            ([], success),
        ]):
            return True

    for size in range(1, 6):
        shared = object()
        items = [shared if index % 2 else EqualResource() for index in range(size)]
        for mask in product((False, True), repeat=size):
            pattern = [
                (errors[index % len(errors)] if failed else None,
                 returns[index % len(returns)])
                for index, failed in enumerate(mask)
            ]
            if _case(mod, items, [
                ([], pattern), ([items[0], None], failure),
                ([False, items[-1]], [(None, False), (errors[0], None)]),
                ([], success), ([], success),
            ]):
                return True

    for size in (31, 32, 33, 64, 65, 257):
        items = [object() for _ in range(size)]
        if _case(mod, items, [
            ([], [(None, False), (errors[0], None), (errors[-1], None)]),
            ([items[0], items[-1], items[0]], failure),
            ([], failure), ([], success), ([], success),
        ]):
            return True

    shared = object()
    long_rounds = []
    for index in range(70):
        long_rounds.append((
            [shared, resources[index % len(resources)]],
            [(errors[index % len(errors)], None), (None, returns[index % len(returns)])],
        ))
    long_rounds.extend([([], success), ([], success)])
    return _case(mod, [], long_rounds)
