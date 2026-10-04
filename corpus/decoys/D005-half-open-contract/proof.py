"""D005 반증 - 마지막 페이지에서 범위를 넘기려 시도한다."""

from __future__ import annotations

import enum
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """총량이 페이지 크기의 배수가 아닐 때 hi 가 넘치는가.

    decoy 는 min(lo + PAGE, total) 로 잘라 IndexError 가 없다.
    twin 은 자르지 않아 마지막 페이지에서 터진다.
    """
    class _Page(int):
        pass

    class _Pages(enum.IntEnum):
        BACK = -1
        NEXT = 1

    for total in (0, 1, 25):  # 음수 page 는 ValueError 로 거절한다 (교차 패밀리 감사 - 전에는 끝에서 거꾸로 셌다)
        for page in (-1, -2, -3, -(10**9), _Page(-1), _Pages.BACK):  # int 하위 타입도 (독립 검토)
            try:
                mod.slice_page([str(i) for i in range(total)], page)
            except ValueError:
                continue
            except IndexError:
                return True
            return True
    # 🔴 빈 목록 · 끝 너머 page 도 그 밖의 page 다 (독립 검토 · 에이전트 지적) - 끝 너머에서 lo > hi 이던 판을 친다
    for total in (0, 1, 7, 10, 11, 25):
        items = [str(i) for i in range(total)]
        pages = (total + 9) // 10
        for page in [*range(pages + 3), 10**9, _Page(1), _Pages.NEXT]:
            try:
                got = mod.slice_page(items, page)
            except IndexError:
                return True
            if got != items[page * 10 : page * 10 + 10]:
                return True
            lo, hi = mod.page_bounds(total, page)
            if not 0 <= lo <= hi <= total:
                return True
    return False
