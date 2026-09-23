"""D008 반증 - 경로 탈출을 시도한다."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

_ESCAPES = ("../../etc/passwd", "..", "../", "a/../../..", "/etc/passwd")


def attack(mod: ModuleType) -> bool:
    """루트 밖의 경로가 통과하는가.

    decoy 는 is_relative_to 로 막는다. twin 은 그 검사가 없다.
    🔴 파일을 읽지 않고 sanitize_path 의 반환값만 본다 - 호스트 상태에
       의존하면 공격의 성패가 환경에 따라 달라진다.
    """
    root = Path("/srv/uploads").resolve()
    for value in _ESCAPES:
        try:
            got = mod.sanitize_path(value)
        except ValueError:
            continue  # 의도한 거절
        if not got.is_relative_to(root):
            return True
    return False
