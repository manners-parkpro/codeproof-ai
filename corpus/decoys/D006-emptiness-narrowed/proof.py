"""D006 반증 - 빈 입력으로 IndexError 를 노린다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """rows[0] 접근이 빈 리스트에서 터지는가.

    decoy 는 `if not rows: return 0` 이 먼저 막는다.
    twin 은 그 분기가 없어 IndexError 로 터진다.
    """
    if mod.total([]) != 0:
        return True
    # 비어 있지 않은 경우의 정확성도 같이 본다 - 가드가 결과를 망치지 않았는지
    rows = [mod.Row(count=n) for n in (1, 2, 3)]
    return mod.total(rows) != 6
