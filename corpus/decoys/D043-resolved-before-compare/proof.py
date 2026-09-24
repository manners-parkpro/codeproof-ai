"""D043 반증 - 정규화 없이 접두사 비교를 통과시키려 시도한다."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

_ESCAPES = ("../../etc/passwd", "..", "a/../../../secret", "sub/../../out")


def attack(mod: ModuleType) -> bool:
    """반환 경로가 정규화 후에도 루트 안인가.

    decoy 는 resolve 를 먼저 해서 .. 가 사라진 뒤 비교한다.
    twin 은 정규화 없이 비교해 상대 요소가 남은 경로를 통과시킨다.
    """
    root = Path("/srv/data")
    for name in _ESCAPES:
        try:
            got = mod.resolve_entry(name)
        except ValueError:
            continue  # 의도한 거절
        if not got.resolve().is_relative_to(root):
            return True
    # 정상 이름이 망가지지 않았는지도 본다
    return mod.resolve_entry("report.csv") != root / "report.csv"
