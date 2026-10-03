"""D092 반증 - 작은 격자의 모든 예약 쌍을 분 단위 정답과 견준다."""

from __future__ import annotations

from types import ModuleType

_STARTS = range(12)
_LENGTHS = range(1, 5)


def attack(mod: ModuleType) -> bool:
    """겹치는 예약을 받거나 겹치지 않는 예약을 거절하는 쌍이 있는가.

    정답은 두 예약이 차지하는 분의 집합이 공통 원소를 갖는지로 낸다 - 비교식을 따라 짜지 않는다.
    맞닿음 · 한 분 겹침 · 포함 · 같은 예약이 전부 이 격자 안에 있다 (DESIGN §3.5 「크기 · 범위」).

    decoy 는 끝을 넣지 않는 경계로 만들어 엄격한 부등호가 정확한 겹침 조건이 된다.
    twin 은 끝을 마지막 분으로 만들어 한 분 겹친 예약을 받는다.
    """
    for s1 in _STARTS:
        for m1 in _LENGTHS:
            for s2 in _STARTS:
                for m2 in _LENGTHS:
                    taken = [mod.Booking(s1, m1)]
                    clash = bool(set(range(s1, s1 + m1)) & set(range(s2, s2 + m2)))
                    if mod.accept(mod.Booking(s2, m2), taken) == clash:
                        return True
    # 🔴 앞선 예약이 둘인 목록과 빈 목록도 친다 - 마지막(또는 첫) 예약만 보는 약화가 이것으로만 드러난다 (독립 검토)
    slots = [(s, m) for s in range(8) for m in range(1, 4)]
    for s1, m1 in slots:
        for s2, m2 in slots:
            first, second = set(range(s1, s1 + m1)), set(range(s2, s2 + m2))
            if first & second:
                continue  # 앞선 두 예약은 서로 겹치지 않아야 한다
            for s3, m3 in slots:
                taken = [mod.Booking(s1, m1), mod.Booking(s2, m2)]
                clash = bool((first | second) & set(range(s3, s3 + m3)))
                if mod.accept(mod.Booking(s3, m3), taken) == clash:
                    return True
    taken: list[object] = []
    if not mod.accept(mod.Booking(5, 2), taken) or len(taken) != 1:
        return True
    # 길이가 없는 예약은 받지 않는다
    try:
        mod.accept(mod.Booking(3, 0), [])
    except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
        return False
    return True
