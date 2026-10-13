"""달력 간격의 반증 시도 - 독립 서수 계산과 경계 및 타입의 교차 탐침을 쓴다."""

from datetime import date, datetime, timedelta, timezone, tzinfo
from enum import Enum
from itertools import product
from types import ModuleType


class DateChild(date):
    pass


class DateGrandchild(DateChild):
    pass


class DateTimeChild(datetime):
    pass


class DateTimeGrandchild(DateTimeChild):
    pass


class DateEnum(date, Enum):
    FIRST = (1, 1, 1)
    LEAP = (2000, 2, 29)
    LAST = (9999, 12, 31)


class DateTimeEnum(datetime, Enum):
    FIRST = (1, 1, 1)
    LEAP = (2000, 2, 29, 23, 59, 59, 999999)
    LAST = (9999, 12, 31)


def _ordinal(value: date) -> int:
    year = value.year - 1
    before = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    leap = value.year % 4 == 0 and (value.year % 100 != 0 or value.year % 400 == 0)
    return (
        365 * year + year // 4 - year // 100 + year // 400
        + before[value.month - 1] + value.day
        + int(leap and value.month > 2)
    )


def _state(value: date) -> tuple:
    fields = (type(value), value.year, value.month, value.day)
    if isinstance(value, datetime):
        fields += (
            value.hour, value.minute, value.second, value.microsecond,
            value.tzinfo, value.fold,
        )
    return fields, dict(getattr(value, "__dict__", {}))


def _values() -> list[date]:
    days = [
        (1, 1, 1), (1, 1, 2), (9999, 12, 30), (9999, 12, 31),
        (1900, 2, 28), (1900, 3, 1), (2000, 2, 28), (2000, 2, 29),
        (2000, 3, 1), (2100, 2, 28), (2100, 3, 1), (1969, 12, 31),
        (1970, 1, 1), (2038, 1, 19), (2024, 12, 31), (2025, 1, 1),
    ]
    days += [(2024, month, 1) for month in range(1, 13)]
    edge = timedelta(hours=24) - timedelta(microseconds=1)
    zones = [
        None, timezone.utc, timezone(timedelta(hours=14)),
        timezone(timedelta(hours=-12)), timezone(edge), timezone(-edge),
        timezone(timedelta(seconds=37, microseconds=1)),
    ]
    values = []
    for index, ymd in enumerate(days):
        values.append(date(*ymd))
        child = (DateChild if index % 2 else DateGrandchild)(*ymd)
        child.note = "unchanged"
        values.append(child)
        values.append(datetime(*ymd))
        values.append(datetime(*ymd, 23, 59, 59, 999999))
        for cls in (datetime, DateTimeChild, DateTimeGrandchild):
            for fold in (0, 1):
                value = cls(*ymd, 0, 1, 2, 3, tzinfo=zones[index % len(zones)], fold=fold)
                if cls is not datetime:
                    value.note = "unchanged"
                values.append(value)
    values.extend(DateEnum)
    values.extend(DateTimeEnum)
    values.append(datetime(2024, 1, 1, tzinfo=tzinfo()))
    values.append(datetime(2024, 1, 2, 23, 59, 59, 999999, tzinfo=tzinfo()))
    return values


def _violates(mod: ModuleType, start: date, end: date) -> bool:
    before = (_state(start), _state(end))
    expected = _ordinal(end) - _ordinal(start)
    try:
        actual = mod.day_distance(start, end)
    except Exception:
        return True
    return (
        not isinstance(actual, int)
        or actual != expected
        or before != (_state(start), _state(end))
    )


def attack(mod: ModuleType) -> bool:
    values = _values()
    for start, end in product(values, repeat=2):
        if _violates(mod, start, end):
            return True
    for start, end in zip(reversed(values), values):
        for _ in range(3):
            if _violates(mod, start, end):
                return True
    for year in range(1600, 2001):
        start = date(year, 2, 28)
        end = datetime(year, 3, 1, 23, 59, 59, 999999)
        if _violates(mod, start, end) or _violates(mod, end, start):
            return True
    return False
