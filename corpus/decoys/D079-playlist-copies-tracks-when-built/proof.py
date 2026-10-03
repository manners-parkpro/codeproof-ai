"""D079 반증 - 재생 목록을 섞은 뒤 넘겨준 원래 목록을 본다."""

from __future__ import annotations

import random
from types import ModuleType

_TRACKS = [f"track-{n:02d}" for n in range(12)]


def attack(mod: ModuleType) -> bool:
    """섞기가 호출자의 리스트를 바꾸는가.

    decoy 는 생성자가 사본을 두어 원래 리스트가 그대로다.
    twin 은 원래 리스트를 붙잡아 제자리 섞기가 호출자에게 보인다.
    """
    original = list(_TRACKS)
    playlist = mod.Playlist(original)
    order = playlist.shuffled(random.Random(7))
    if original != _TRACKS:
        return True
    # 섞인 결과는 같은 곡들의 다른 순서여야 한다 - 「아무것도 안 함」은 안전이 아니다
    return sorted(order) != sorted(_TRACKS) or order == _TRACKS
