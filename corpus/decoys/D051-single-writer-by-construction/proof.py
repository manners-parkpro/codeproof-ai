"""D051 반증 - 동시 집계로 갱신 손실을 노린다."""

from __future__ import annotations

from types import ModuleType

from codeproof_ai.corpus.proof import race_window

# 🔴 경쟁은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 5

# 🔴 워커가 겹쳐야 경쟁이 난다. 일이 적으면 앞 워커가 다음 워커가 뜨기 전에 끝난다 -
#    [실측] CPU 를 포화시키면 300 개에서 twin 1회 성공 39/100 이었고, CI macOS 에서 5회 전부
#    실패한 적이 있다. 3000 개면 같은 포화에서 100/100 · decoy 를 깬 횟수 0/100.
_ITEMS = 3000


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
