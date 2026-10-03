"""예약 충돌 검사 - 끝 시각은 그 분을 포함하지 않는 경계다."""

from typing import NamedTuple


class Booking(NamedTuple):
    start: int
    minutes: int


def _end(booking: Booking) -> int:
    return booking.start + booking.minutes


def _overlaps(a: Booking, b: Booking) -> bool:
    return a.start < _end(b) and b.start < _end(a)


def accept(new: Booking, taken: list[Booking]) -> bool:
    if new.minutes <= 0:
        raise ValueError(f"길이가 없는 예약: {new}")
    if any(_overlaps(new, other) for other in taken):
        return False
    taken.append(new)
    return True
