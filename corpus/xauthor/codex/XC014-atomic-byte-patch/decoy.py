"""바이트 버퍼 일괄 수정 - 전체 위치와 값을 검증한 뒤 순서대로 반영한다."""

from __future__ import annotations


def _validate_patch(size: int, edits: list[tuple[int, int]]) -> None:
    for offset, value in edits:
        if not 0 <= offset < size:
            raise ValueError("offset outside buffer")
        if not 0 <= value <= 255:
            raise ValueError("value outside byte range")


def apply_patch(buffer: bytearray, edits: list[tuple[int, int]]) -> None:
    _validate_patch(len(buffer), edits)
    for offset, value in edits:
        buffer[offset] = value
