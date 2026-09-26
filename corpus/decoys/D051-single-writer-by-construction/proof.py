"""D051 반증 - 동시 집계로 갱신 손실을 노린다."""

from __future__ import annotations

from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 경쟁은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

_ITEMS = 300


def attack(mod: ModuleType) -> bool:
    """워커가 여럿이면 합계가 줄어드는가.

    총 작업량은 양쪽이 같다 - 다른 것은 **동시에 도느냐**뿐이다.

    decoy 는 run 이 워커를 하나만 만들어 경쟁 상대가 없다.
    twin 은 값을 쪼개 넷을 띄워 read-modify-write 가 겹친다.
    """
    mod._totals["sum"] = 0
    values = list(range(_ITEMS))

    with race_window("_accumulate"):
        got = mod.run(values)

    return got != sum(values) or mod._totals["sum"] != sum(values)
