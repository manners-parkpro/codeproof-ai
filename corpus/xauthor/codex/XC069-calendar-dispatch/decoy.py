"""두 달력 날짜의 간격 계산 - 타입별 디스패치가 시각 입력을 날짜로 좁힌다."""

from datetime import date, datetime
from functools import singledispatch


@singledispatch
def _calendar_day(value: date) -> date:
    return value


@_calendar_day.register(datetime)
def _datetime_day(value: datetime) -> date:
    return value.date()


def day_distance(start: date, end: date) -> int:
    left = _calendar_day(start)
    right = _calendar_day(end)
    return (right - left).days
