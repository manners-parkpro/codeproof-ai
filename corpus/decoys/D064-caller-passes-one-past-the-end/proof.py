"""D064 반증 - 번호 줄에서 끝 번호가 빠지는지 본다."""

from __future__ import annotations

from types import ModuleType

_CASES = ((5, 10), (1, 1), (10, 10), (2, 3), (7, 9))


def attack(mod: ModuleType) -> bool:
    """현재 쪽을 가운데 둔 번호 줄이 first..final 을 빠짐없이 담는가.

    decoy 는 page_links 가 final + 1 을 넘겨 range 의 배타적 상한과 맞는다.
    twin 은 final 을 그대로 넘겨 range 가 끝 번호를 뺀다.
    """
    for current, last in _CASES:
        want = list(range(max(1, current - 2), min(last, current + 2) + 1))
        if mod.page_links(current, last) != want:
            return True
    return False
