"""주장의 각 절을 독립적인 결과 오라클로 반증한다."""

from itertools import product
from types import ModuleType


class MissingChild(FileNotFoundError):
    pass


class PermissionChild(PermissionError):
    pass


class FatalChild(BaseException):
    pass


class GroupChild(BaseExceptionGroup):
    pass


class OrdinaryGroupChild(ExceptionGroup):
    pass


def _leaves(error: BaseException) -> list[BaseException]:
    result = []
    cursors = [iter((error,))]
    while cursors:
        try:
            item = next(cursors[-1])
        except StopIteration:
            cursors.pop()
            continue
        if isinstance(item, BaseExceptionGroup):
            cursors.append(iter(item.exceptions))
        else:
            result.append(item)
    return result


def _run(mod: ModuleType, failure: BaseException | None, value: object,
         expected: list[BaseException]) -> bool:
    calls = []
    result = object()
    observed = []

    def cleanup() -> object:
        calls.append(None)
        if failure is not None:
            raise failure
        return value

    try:
        result = mod.cleanup_optional(cleanup)
    except BaseException as error:
        observed = _leaves(error)
    if len(calls) != 1:
        return True
    if len(observed) != len(expected):
        return True
    if any(actual is not wanted for actual, wanted in zip(observed, expected)):
        return True
    return not expected and result is not None


def attack(mod: ModuleType) -> bool:
    missing = FileNotFoundError("gone")
    missing_child = MissingChild("gone too")
    denied = PermissionError("denied")
    denied_child = PermissionChild("child denied")
    fatal = FatalChild("fatal")
    interrupted = KeyboardInterrupt()
    exits = SystemExit(0)
    values = (None, False, True, 0, -1, 10 ** 200, "", [], {}, object(),
              missing, denied, BaseExceptionGroup("returned", [missing, fatal]))
    for value in values:
        if _run(mod, None, value, []):
            return True

    cases = [
        (missing, []),
        (missing_child, []),
        (FileNotFoundError(), []),
        (FileNotFoundError(13, "unusual errno"), []),
        (OSError(2, "constructor dispatch"), []),
    ]
    errors = [
        denied, denied_child, fatal, interrupted, exits, GeneratorExit(),
        BaseException(), Exception(), RuntimeError(""), ValueError(),
        OSError(), OSError(0, ""), FileExistsError(), IsADirectoryError(),
        NotADirectoryError(), TimeoutError(), StopIteration(), StopAsyncIteration(),
        RecursionError(), AssertionError(), UnicodeError(),
    ]
    cases.extend((error, [error]) for error in errors)
    for group_type in (ExceptionGroup, OrdinaryGroupChild):
        cases.extend([
            (group_type("missing", [missing, missing_child]), []),
            (group_type("mixed", [missing, denied, missing_child, denied_child]),
             [denied, denied_child]),
        ])
    for group_type in (BaseExceptionGroup, GroupChild):
        cases.extend([
            (group_type("missing", [missing, missing_child]), []),
            (group_type("fatal", [fatal, interrupted, exits]),
             [fatal, interrupted, exits]),
            (group_type("mixed", [missing, fatal, missing_child, denied]),
             [fatal, denied]),
        ])
    for first, second, third in product((missing, denied, fatal), repeat=3):
        cases.append((
            BaseExceptionGroup("positions", [
                first, BaseExceptionGroup("nested", [second]), third]),
            [x for x in (first, second, third) if x is not missing],
        ))
    shared = BaseExceptionGroup("shared", [denied, missing, fatal, denied])
    cases.extend([
        (BaseExceptionGroup("repeated", [shared, shared]),
         [denied, fatal, denied, denied, fatal, denied]),
        (BaseExceptionGroup("ordering", [
            BaseExceptionGroup("left", [
                denied, BaseExceptionGroup("deeper", [fatal, missing])]),
            denied_child, BaseExceptionGroup("right", [exits, missing_child])]),
         [denied, fatal, denied_child, exits]),
    ])
    for leaf, expected in ((missing, []), (missing_child, []),
                           (denied, [denied]), (fatal, [fatal])):
        deep = leaf
        for _ in range(2500):
            deep = BaseExceptionGroup("depth", [missing, deep, missing_child])
        cases.append((deep, expected))
    wide_leaves = [ValueError(i) for i in range(2048)]
    wide = []
    for leaf in wide_leaves:
        wide.extend((missing, leaf))
    cases.extend([
        (ExceptionGroup("wide missing", [missing, missing_child] * 2048), []),
        (ExceptionGroup("wide mixed", wide), wide_leaves),
    ])
    for failure, expected in cases:
        if _run(mod, failure, None, expected):
            return True
    return False
