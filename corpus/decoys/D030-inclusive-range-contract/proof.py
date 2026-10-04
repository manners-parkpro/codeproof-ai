"""D030 반증 - 경계 점수가 어느 구간에도 안 속하는지 본다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """0~100 의 모든 점수가 정확히 한 등급을 받는가.

    🔴 등급이 맞는지와 0~100 밖을 거절하는지도 본다 - 예외 없이 등급만 내는지 보면 경계를 한 칸 옮긴 약화가 지나갔다
       (독립 검토). 거절의 예외 타입은 주장이 정하지 않으므로 묻지 않는다.

    decoy 는 <= 가 계약과 맞아 빈틈이 없다.
    twin 은 각 구간의 상한이 떨어져 나가 ValueError 가 난다.
    """
    want = {s: lab for lo, hi, lab in ((0, 59, "F"), (60, 79, "C"), (80, 89, "B"), (90, 100, "A")) for s in range(lo, hi + 1)}
    for score in range(101):
        try:
            got = mod.grade(score)
        except ValueError:
            return True  # 구간에 빈틈이 있다
        if got != want[score]:
            return True  # 이웃 구간과 겹친다 - 경계 점수가 다른 등급을 받는다
    for score in (-1, 101):  # 어느 구간에도 들지 않는다 - 예외 타입은 주장이 정하지 않으므로 묻지 않는다
        try:
            mod.grade(score)
        except Exception:  # noqa: BLE001
            continue
        return True

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
