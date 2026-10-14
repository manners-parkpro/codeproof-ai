"""예약과 겹치는 행 검색 - 반열린 경계에 닿기만 하는 하위 트리는 제외한다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Node:
    lower: int
    upper: int
    row: int | None = None
    left: _Node | None = None
    right: _Node | None = None


def _build(nodes: list[_Node]) -> _Node:
    if len(nodes) == 1:
        return nodes[0]
    middle = len(nodes) // 2
    left = _build(nodes[:middle])
    right = _build(nodes[middle:])
    return _Node(
        min(left.lower, right.lower),
        max(left.upper, right.upper),
        left=left,
        right=right,
    )


def _collect(node: _Node, start: int, stop: int, result: list[int]) -> None:
    """반열린 예약 [lower, upper)와 [start, stop)가 겹치는 행 번호를 입력 순서로 추가한다."""
    if node.upper < start or node.lower >= stop:
        return
    if node.row is not None:
        result.append(node.row)
        return
    if node.left is not None:
        _collect(node.left, start, stop, result)
    if node.right is not None:
        _collect(node.right, start, stop, result)


def overlapping_rows(spans: list[tuple[int, int]], start: int, stop: int) -> list[int]:
    if start > stop or any(lower > upper for lower, upper in spans):
        raise ValueError("reversed interval")
    nodes = [_Node(lower, upper, row) for row, (lower, upper) in enumerate(spans) if lower < upper]
    if start == stop or not nodes:
        return []
    result: list[int] = []
    _collect(_build(nodes), start, stop, result)
    return result
