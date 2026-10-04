"""D142 반증 - date · datetime 과 그 하위 타입, 시간대가 붙은 자정 근처 시각으로 열쇠를 받아, 연 · 월 · 일로 만든 기대와 견준다."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
from types import ModuleType


class _Day(date):
    """메서드를 재정의하지 않은 date 하위 클래스."""


class _Moment(datetime):
    """메서드를 재정의하지 않은 datetime 하위 클래스."""


class _Holiday(date, Enum):
    NEW_YEAR = (2024, 1, 1)


class _Launch(datetime, Enum):
    T0 = (2024, 3, 1, 23, 30)


def _values() -> list[date]:
    zones = [None, timezone.utc, timezone(timedelta(hours=14)), timezone(timedelta(hours=-12)), timezone(timedelta(hours=5, minutes=30))]
    out: list[date] = [date(2024, 3, 1), date(2024, 2, 29), date.min, date.max, date(999, 12, 31), date(1, 1, 1), _Day(2023, 7, 4)]
    for tz in zones:
        out += [
            datetime(2024, 3, 1, 10, 30, tzinfo=tz),
            datetime(2024, 3, 1, 0, 0, tzinfo=tz),
            datetime(2024, 3, 1, 23, 59, 59, 999999, tzinfo=tz),
            datetime(1, 1, 1, 0, 0, tzinfo=tz),
            datetime(9999, 12, 31, 23, 59, tzinfo=tz),
            _Moment(2022, 12, 31, 23, 0, tzinfo=tz),
        ]
    out.append(datetime(2024, 11, 3, 1, 30, fold=1))
    out += [_Holiday.NEW_YEAR, _Launch.T0]
    return out


def attack(mod: ModuleType) -> bool:
    """열쇠가 그 값에 적힌 연 · 월 · 일의 YYYY-MM-DD 가 아니면 True - 시각이 붙거나 다른 시간대의 날짜가 되어도 깨진다.

    🔴 기대는 year · month · day 로 만든다 - isoformat 을 다시 불러 견주지 않는다.
    🔴 datetime 의 하위 클래스를 친다 - type(value) is datetime 으로 고르는 판이 빠지지 않게.
    🔴 (date, Enum) · (datetime, Enum) 혼합형도 친다 - str() 이 이름을 돌려주므로 str() 로 날짜를 꺼내는 판이 빠지지 않게.
    🔴 시간대가 붙은 자정 근처 시각을 친다 - UTC 로 옮긴 뒤 날짜를 뽑는 판은 날짜가 바뀐다.

    decoy 는 bucket 이 datetime 을 먼저 date 로 바꾼 뒤 _day_key 를 부른다.
    twin 은 바꾸지 않아 datetime 의 열쇠에 시각이 붙는다.
    """
    for value in _values():
        want = f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
        if mod.bucket(value) != want:
            return True
    return False
