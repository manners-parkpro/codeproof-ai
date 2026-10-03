"""D078 반증 - 여러 선택에서 꺼낸 줄 수와 내용을 맞춰 본다."""

from __future__ import annotations

from types import ModuleType

_LINES = [f"L{n}" for n in range(1, 11)]
_CASES = ((1, 1), (3, 2), (1, 10), (10, 1), (4, 0), (7, 3), (11, 0))


def attack(mod: ModuleType) -> bool:
    """선택한 줄이 하나라도 빠지거나 더 붙는가.

    decoy 는 of 가 stop 을 마지막 줄 다음으로 만들어 stop - 1 이 0부터 세는 반열린 끝이 된다.
    twin 은 stop 을 마지막 줄로 만들어 같은 슬라이스가 마지막 줄을 빠뜨린다.
    """
    for first, count in _CASES:
        want = _LINES[first - 1 : first - 1 + count]
        if mod.selected(_LINES, mod.LineSpan.of(first, count)) != want:
            return True

    # 잘못된 범위는 조용히 줄여 돌려주지 않고 거절한다 - 음수 count 와 lines 를 넘는 범위
    for first, count in ((0, 1), (1, -1)):
        try:
            mod.LineSpan.of(first, count)
        except ValueError:
            continue
        return True
    for first, count in ((9, 5), (11, 1), (1, 11)):
        try:
            mod.selected(_LINES, mod.LineSpan.of(first, count))
        except IndexError:
            continue
        return True
    return False
