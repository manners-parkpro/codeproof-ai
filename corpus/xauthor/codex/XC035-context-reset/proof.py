"""요청 스코프의 반증 - 종료 결과와 중첩 깊이를 교차하여 바인딩 및 예외 객체를 관찰한다."""

from contextvars import Context
from enum import Enum
from types import ModuleType


class RequestText(str):
    pass


class NamedRequest(str, Enum):
    EMPTY = ""
    ALPHA = "alpha"


class CleanupSignal(BaseException):
    pass


def _case(mod, values, body_kind, finish_kind, nested_finish, same_error):
    failures = []
    body_error = None if body_kind is None else body_kind("body")
    finish_error = None if finish_kind is None else finish_kind("finish")
    if same_error:
        finish_error = body_error
    extra = RequestText("finish-child")

    def observe(expected):
        if mod.current_request() is not expected:
            failures.append("binding")

    def scope(value, previous, child, finish_child):
        events = []

        def finish():
            events.append("finish")
            observe(value)
            if finish_child:
                scope(extra, value, None, False)
                observe(value)
            if finish_error is not None:
                raise finish_error

        caught = None
        observe(previous)
        try:
            with mod.request_scope(value, finish) as bound:
                events.append("body")
                if bound is not value:
                    failures.append("yield")
                observe(value)
                if child is not None:
                    child()
                observe(value)
                events.append("body-end")
                if body_error is not None:
                    raise body_error
        except BaseException as exc:
            caught = exc
        observe(previous)
        if caught is not body_error:
            failures.append("exception")
        if events != ["body", "body-end", "finish"]:
            failures.append("lifecycle")

    def visit(index):
        previous = None if index == 0 else values[index - 1]
        child = None
        if index + 1 < len(values):
            child = lambda: visit(index + 1)
        scope(values[index], previous, child, nested_finish)

    observe(None)
    for _ in range(3):
        visit(0)
        observe(None)
    return bool(failures)


def _group(message):
    return ExceptionGroup(message, [ValueError(message), RuntimeError(message)])


def _base_group(message):
    return BaseExceptionGroup(message, [KeyboardInterrupt(message), ValueError(message)])


def attack(mod: ModuleType) -> bool:
    errors = (
        None, Exception, ValueError, RuntimeError, BaseException,
        KeyboardInterrupt, SystemExit, GeneratorExit, StopIteration,
        StopAsyncIteration, CleanupSignal, _group, _base_group,
    )
    equal_a = RequestText("same")
    equal_b = RequestText("same")
    paths = (
        ("request",),
        ("",),
        (RequestText("subclass"),),
        (NamedRequest.EMPTY, NamedRequest.ALPHA, ""),
        ("outer", "middle", "inner"),
        (equal_a, equal_b, equal_a),
        ("\x00\n\u2028", "한글", "x" * 65536),
        tuple(RequestText(str(n)) for n in range(16)),
    )
    try:
        for values in paths:
            for body_kind in errors:
                for finish_kind in errors:
                    if Context().run(
                        _case, mod, values, body_kind, finish_kind, False, False
                    ):
                        return True
        for body_kind in errors:
            for finish_kind in errors:
                if Context().run(
                    _case, mod, paths[4], body_kind, finish_kind, True, False
                ):
                    return True
        for kind in errors[1:]:
            if Context().run(_case, mod, paths[5], kind, kind, True, True):
                return True
    except BaseException:
        return True
    return False
