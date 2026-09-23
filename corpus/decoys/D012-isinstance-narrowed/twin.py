"""이벤트 처리 - isinstance 가 타입을 좁힌다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextEvent:
    body: str


@dataclass(frozen=True)
class BinaryEvent:
    payload: bytes


def summarize(event: TextEvent | BinaryEvent) -> str:
    return event.body.strip().lower()
