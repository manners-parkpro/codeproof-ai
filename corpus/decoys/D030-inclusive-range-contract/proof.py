"""D030 반증 - 경계 점수가 어느 구간에도 안 속하는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """0~100 의 모든 점수가 정확히 한 등급을 받는가.

    decoy 는 <= 가 계약과 맞아 빈틈이 없다.
    twin 은 각 구간의 상한이 떨어져 나가 ValueError 가 난다.
    """
    for score in range(101):
        try:
            mod.grade(score)
        except ValueError:
            return True  # 구간에 빈틈이 있다

    # 구간 크기 계산이 채점과 일관되는지도 본다
    covered = sum(mod.band_size(low, high) for low, high, _ in mod._BANDS)
    if covered != 101:
        return True
    # 🔴 _BANDS 밖의 경계도 같은 계약이다 (교차 패밀리 감사) - 역순 구간은 0 개를 담는다
    for low in range(-3, 4):
        for high in range(-3, 4):
            if mod.band_size(low, high) != sum(1 for s in range(-5, 6) if low <= s <= high):
                return True
    return False
