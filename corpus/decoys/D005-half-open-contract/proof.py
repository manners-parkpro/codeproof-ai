"""D005 반증 - 마지막 페이지에서 범위를 넘기려 시도한다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """총량이 페이지 크기의 배수가 아닐 때 hi 가 넘치는가.

    decoy 는 min(lo + PAGE, total) 로 잘라 IndexError 가 없다.
    twin 은 자르지 않아 마지막 페이지에서 터진다.
    """
    for total in (1, 7, 10, 11, 25):
        items = [str(i) for i in range(total)]
        pages = (total + 9) // 10
        for page in range(pages):
            try:
                got = mod.slice_page(items, page)
            except IndexError:
                return True
            if got != items[page * 10 : page * 10 + 10]:
                return True
    return False
