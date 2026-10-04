"""D138 반증 - 돌려받은 한도 객체를 여러 방법으로 고쳐 본 뒤, 모든 요금제의 한도가 처음 값인지 본다."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

_LIMITS = {"FREE": (3, 1), "TEAM": (50, 10)}  # 주장 문장 그대로


def _attempts() -> list[Callable[[object], None]]:
    """평범하게 고치는 방법 - 대입 · 늘리기 · 삭제 · setattr · 새 속성 (object.__setattr__ 같은 의도적 우회는 위협 모델 밖)."""

    def assign(obj: object) -> None:
        obj.projects = 1000  # type: ignore[attr-defined]

    def assign_small(obj: object) -> None:
        obj.projects = 1  # type: ignore[attr-defined]

    def shrink(obj: object) -> None:
        obj.projects -= 1  # type: ignore[attr-defined]

    def shrink_seats(obj: object) -> None:
        obj.seats -= 1  # type: ignore[attr-defined]

    def grow(obj: object) -> None:
        obj.seats += 5  # type: ignore[attr-defined]

    def remove(obj: object) -> None:
        del obj.projects  # type: ignore[attr-defined]

    def remove_seats(obj: object) -> None:
        del obj.seats  # type: ignore[attr-defined]

    def via_setattr(obj: object) -> None:
        setattr(obj, "seats", 0)  # noqa: B010 - 이름으로 고치는 길도 친다

    def extra(obj: object) -> None:
        obj.projects_override = 99  # type: ignore[attr-defined]

    return [assign, assign_small, shrink, grow, shrink_seats, remove, remove_seats, via_setattr, extra]


def _now(mod: ModuleType) -> dict[str, tuple[int, int]]:
    return {plan.name: (mod.limits_for(plan).projects, mod.limits_for(plan).seats) for plan in mod.Plan}


def attack(mod: ModuleType) -> bool:
    """처음 한도가 주장과 다르거나, 돌려받은 객체를 고친 뒤 어느 요금제의 한도라도 바뀌는가.

    🔴 고친 요금제만이 아니라 모든 요금제를 다시 본다 - 한도 객체를 요금제끼리 나눠 쓰는 판이 빠지지 않게.
    🔴 삭제는 두 필드 모두 친다 - projects 만 지워 보면 seats 의 삭제를 빠뜨린 판이 빠진다.
    🔴 대입은 두 필드 모두 늘리기 · 줄이기 · 범위 안의 작은 값까지 친다 - 범위를 보거나 늘리기만 막는 setter 를 둔 판은
       큰 값 하나로는 보이지 않는다 (6라운드 검토).
    🔴 거절 방식은 묻지 않는다 - 거절되든 받아들여져 사본만 바뀌든, 다음 limits_for 가 처음 값이면 된다.

    decoy 는 한도 객체가 frozen · slots 인 dataclass 라 고치는 시도가 모두 거절된다.
    twin 은 frozen 이 아니라 한 번 고치면 그 요금제의 모든 사용자에게 남는다.
    """
    if _now(mod) != _LIMITS:
        return True
    for attempt in _attempts():
        for plan in mod.Plan:
            try:
                attempt(mod.limits_for(plan))
            except Exception:  # noqa: BLE001, S112 - 거절은 정상이다
                pass
            if _now(mod) != _LIMITS:
                return True
    return False
