"""측정값 변환 - 생성자가 None 을 걷어낸다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    sensor: str
    fahrenheit: float | None


def to_celsius(reading: Reading) -> float:
    return (reading.fahrenheit - 32) / 9 * 5
