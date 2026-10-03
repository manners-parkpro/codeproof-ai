"""예약 시각 저장 - 시간대가 없는 시각은 바꾸기 전에 확인 함수가 거절한다."""

import datetime


def _aware(when: datetime.datetime) -> datetime.datetime:
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError(f"시간대가 없는 시각: {when!r}")
    return when


def to_storage(when: datetime.datetime) -> str:
    checked = _aware(when)
    return checked.astimezone(datetime.UTC).isoformat()
