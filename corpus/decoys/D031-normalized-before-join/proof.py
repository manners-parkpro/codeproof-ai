"""D031 반증 - 루트 밖 경로를 만들려 시도한다."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

_ESCAPES = (
    "../../etc/passwd",
    "..",
    "a/../../secret.bin",
    "/etc/passwd",
    "deadbeef.bin/../../x",
)


def attack(mod: ModuleType) -> bool:
    """반환 경로가 _ROOT 밖으로 나가는가.

    🔴 파일을 읽지 않는다 - 호스트 상태에 기대면 공격의 성패가 환경에 따라 달라진다.

    decoy 는 normalize 가 정규식으로 막는다. twin 은 검사 없이 결합한다.
    """
    root = Path("/srv/attachments")
    for name in _ESCAPES:
        try:
            got = mod.locate(name)
        except ValueError:
            continue  # 의도한 거절
        if not got.resolve().is_relative_to(root.resolve()):
            return True
    # 정상 이름이 망가지지 않았는지도 본다
    return mod.locate("deadbeef.bin") != root / "deadbeef.bin"
