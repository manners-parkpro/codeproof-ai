"""날짜별로 묶을 열쇠 - 날짜 부분만 쓰는 도우미는 bucket 이 datetime 을 date 로 바꾼 뒤에만 부른다."""

from datetime import date, datetime


def _day_key(day: date) -> str:
    return day.isoformat()


def bucket(value: date | datetime) -> str:
    return _day_key(value)
