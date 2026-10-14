"""정리 영수증 반증 - 취소와 실행 및 완료의 상태 전이를 외부 관찰로 확인한다."""

from concurrent.futures import CancelledError, Future
from datetime import datetime
from enum import Enum, IntEnum
from types import ModuleType


class PlainObject:
    pass


class PlainInt(int):
    pass


class Number(IntEnum):
    ZERO = 0
    ONE = 1


class Text(str, Enum):
    EMPTY = ""
    VALUE = "receipt"


class PlainError(Exception):
    pass


class PlainBaseError(BaseException):
    pass


class PlainGroup(BaseExceptionGroup):
    pass


def _capture(call):
    try:
        return False, call()
    except BaseException as error:
        return True, error


def _pending(ticket, running):
    if ticket.done() or ticket.cancelled() or ticket.running() is not running:
        return False
    for read in (ticket.result, ticket.exception):
        raised, value = _capture(lambda: read(timeout=0))
        if not raised or not isinstance(value, TimeoutError):
            return False
    return True


def _cancelled(ticket):
    if not ticket.done() or not ticket.cancelled() or ticket.running():
        return False
    if ticket.cancel() is not True:
        return False
    for read in (ticket.result, ticket.exception):
        raised, value = _capture(lambda: read(timeout=0))
        if not raised or not isinstance(value, CancelledError):
            return False
    return True


def _valid(record):
    ticket = record["ticket"]
    if record["cancel"]:
        return not record["calls"] and _cancelled(ticket)
    if not record["ran"]:
        return not record["calls"] and _pending(ticket, False)
    if record["calls"] != [True] or record["live"] != [True]:
        return False
    if not ticket.done() or ticket.cancelled() or ticket.running() or ticket.cancel():
        return False
    error = record["error"]
    for _ in range(3):
        raised, value = _capture(lambda: ticket.exception(timeout=0))
        if raised or value is not error:
            return False
        raised, value = _capture(lambda: ticket.result(timeout=0))
        if error is None:
            if raised or value is not None:
                return False
        elif not raised or value is not error:
            return False
    return record["calls"] == [True]


def _prepare(mod, value, error, cancel):
    record = {
        "error": error,
        "cancel": cancel,
        "ran": False,
        "calls": [],
        "live": [],
    }

    def dispose():
        record["calls"].append(True)
        ticket = record["ticket"]
        record["live"].append(_pending(ticket, True) and ticket.cancel() is False)
        if error is not None:
            raise error
        return value

    raised, pair = _capture(lambda: mod.prepare_cleanup(dispose))
    if raised:
        return None
    ticket, run = pair
    record["ticket"] = ticket
    record["run"] = run
    if not isinstance(ticket, Future) or record["calls"] or not _pending(ticket, False):
        return None
    if cancel and (ticket.cancel() is not True or not _cancelled(ticket)):
        return None
    return record


def attack(mod: ModuleType) -> bool:
    shared = PlainObject()
    values = [
        None, False, True, 0, -1, 10**400, -(10**400),
        1.7976931348623157e308, -1.7976931348623157e308,
        "", "정리", b"", [], {}, (), shared, shared, PlainInt(0),
        Number.ZERO, Number.ONE, Text.EMPTY, Text.VALUE,
        datetime.min, datetime.max, ValueError("returned"), KeyboardInterrupt(),
    ]
    leaf = PlainError("repeated")
    nested = BaseExceptionGroup("bottom", [leaf, SystemExit(7), leaf])
    for _ in range(80):
        nested = BaseExceptionGroup("nested", [nested])
    errors = [
        Exception(), ValueError("failed"), PlainError(), BaseException(),
        PlainBaseError(), KeyboardInterrupt(), SystemExit(0), SystemExit(17),
        GeneratorExit(), StopIteration(shared), StopAsyncIteration(shared),
        CancelledError(), TimeoutError(), AssertionError(),
        ExceptionGroup("ordinary", [leaf, ValueError(), leaf]),
        PlainGroup("subtype", [KeyboardInterrupt(), leaf]),
        BaseExceptionGroup("wide", [leaf] * 257 + [GeneratorExit()]),
        nested,
    ]
    specs = [(value, None, False) for value in values]
    specs += [(shared, error, False) for error in errors]
    specs += [(value, None, True) for value in values]
    specs += [(shared, error, True) for error in errors]
    records = []
    for wave in (specs, list(reversed(specs))):
        current = []
        for value, error, cancel in wave:
            record = _prepare(mod, value, error, cancel)
            if record is None:
                return True
            records.append(record)
            current.append(record)
            if not all(_valid(old) for old in records):
                return True
        order = current[::2] + list(reversed(current[1::2]))
        for record in order:
            raised, value = _capture(record["run"])
            record["ran"] = True
            if raised or value is not None:
                return True
            if not all(_valid(old) for old in records):
                return True
    return False
