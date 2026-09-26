"""D045 반증 - 순회 중 삭제가 터지는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """만료 항목이 섞여 있을 때 순회가 완주하는가.

    decoy 는 list(...) 사본을 돌아 원본 변경에 영향받지 않는다.
    twin 은 뷰를 직접 돌아 첫 삭제에서 RuntimeError 가 난다.
    """
    mod._sessions.clear()
    mod._sessions.update({f"s{i}": i for i in range(10)})

    try:
        removed = mod.sweep(4)
    except RuntimeError:
        return True  # 순회 중 변경으로 터졌다

    if removed != 5:
        return True
    return sorted(mod._sessions) != [f"s{i}" for i in range(5, 10)]
