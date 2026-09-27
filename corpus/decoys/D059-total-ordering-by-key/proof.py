"""D059 반증 - 동점 우선순위에서 삽입 순서가 지켜지는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """같은 우선순위 항목이 넣은 순서대로 나오는가.

    decoy 는 순번이 tie-breaker 라 삽입 순서가 유지된다.
    twin 은 payload 가 비교에 들어가 사전순이 된다.
    """
    mod._heap.clear()
    # 사전순과 삽입 순서가 어긋나도록 고른다
    inserted = ["zebra", "apple", "mango"]
    for payload in inserted:
        mod.push(1, payload)

    if [mod.pop() for _ in inserted] != inserted:
        return True

    # 우선순위 자체는 여전히 우선해야 한다
    mod.push(5, "low")
    mod.push(1, "high")
    return mod.pop() != "high"
