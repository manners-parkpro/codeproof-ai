"""정수 타임스탬프의 단위 변환 - 양수 주파수와 전 항목의 정수 표현 가능성을 먼저 검사한다."""

from __future__ import annotations


def _validate_ticks(ticks: list[int], source_hz: int, target_hz: int) -> None:
    if source_hz <= 0 or target_hz <= 0:
        raise ValueError("frequencies must be positive")
    if any((tick * target_hz) % source_hz != 0 for tick in ticks):
        raise ValueError("timestamp cannot be represented exactly")


def rescale_ticks(ticks: list[int], source_hz: int, target_hz: int) -> list[int]:
    return [tick * target_hz // source_hz for tick in ticks]
