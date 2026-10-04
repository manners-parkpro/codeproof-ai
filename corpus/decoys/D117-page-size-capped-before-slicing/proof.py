"""D117 반증 - 여러 offset · limit 으로 쪽을 받아 개수와 내용, 거절을 본다."""

from __future__ import annotations

import itertools
from types import ModuleType

_ITEMS = [f"row-{n}" for n in range(1000)]
# 🔴 어떤 items 든 - 한 쪽보다 짧은 목록 · 빈 목록 · 같은 값이 겹친 목록도 친다 (쓰는 단계 점검)
_LISTS = [_ITEMS, _ITEMS[:5], _ITEMS[:150], [], ["dup"] * 30]
# 받아들일 offset - 처음 · 중간 · 끝 근처 · 끝 · 끝 너머 · sys.maxsize 근처와 너머 · bool(False 는 0)
_OFFSETS = [0, 1, 450, 950, 999, 1000, 5000, 2**63 - 100, 2**63, 10**30, False]
# 받아들일 limit - 1 · 상한 근처 · 상한 · 상한 너머 · 아주 큼 · bool(True 는 1)
_LIMITS = [1, 2, 99, 100, 101, 150, 999, 10**6, 2**63, True]
# 거절할 요청 - 음수 offset · 1 보다 작은 limit
_REJECTED = [(-1, 10), (-1000, 10), (0, 0), (0, -5), (10, -(10**6))]


def attack(mod: ModuleType) -> bool:
    """받아들일 요청이 items[offset:] 의 앞쪽 min(limit, 100)개가 아니거나, 거절할 요청을 받는가.

    🔴 limit 을 상한 너머까지 · 아주 크게 친다 - 상한 근처만 치면 「상한 두 배까지」 같은 약화가 빠진다.
    🔴 받아들인 요청은 내용까지 본다 - 개수만 보면 「상한을 넘으면 비운다」 같은 약화가 지나간다.
    🔴 받아들일 요청을 거절하는 것도 깨짐이다 - 주장은 0 이상의 offset 과 1 이상의 limit 을 받아들인다고 말한다.
       sys.maxsize 를 넘는 offset 도 받아들인다 - islice 로 자르는 판은 거기서 ValueError 다 (쓰는 단계 점검).
    🔴 거절할 요청의 거절 방식은 묻지 않는다 - 어떤 예외든 거절이다.

    decoy 는 자르기 전에 limit 을 100 으로 줄이고, 음수 offset 과 1 보다 작은 limit 을 거절한다.
    twin 은 limit 을 줄이지 않아 큰 limit 에 목록 전체를 돌려준다.
    """
    for items in _LISTS:
        for offset in _OFFSETS:
            for limit in _LIMITS:
                try:
                    got = mod.page(list(items), offset, limit)
                except Exception:  # noqa: BLE001 - 받아들일 요청을 어떤 예외로든 거절하면 깨진 것이다
                    return True
                if got != items[offset:][: min(limit, 100)]:
                    return True
    # 🔴 거절 절도 어떤 items 든이다 - 1000개 목록 하나로만 치면 확인 앞의 「빈 목록 · 끝 너머 빠른 길」이 지나간다 (독립 검토)
    for (offset, limit), items in itertools.product(_REJECTED, _LISTS):
        try:
            mod.page(list(items), offset, limit)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
