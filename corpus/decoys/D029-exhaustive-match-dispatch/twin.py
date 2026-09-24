"""이벤트 디스패치 - 열거가 전수 처리된다."""

from enum import StrEnum


class Signal(StrEnum):
    START = "start"
    STOP = "stop"
    PING = "ping"


_UNSET: dict[str, int] = {}


def priority(signal: Signal) -> int:
    match signal:
        case Signal.START:
            return 0
        case Signal.STOP:
            return 1
    return _UNSET["missing"]
