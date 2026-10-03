"""D101 반증 - 이름이 비슷하거나 모르는 배송 방식으로 견적을 낸다."""

from __future__ import annotations

from types import ModuleType


class _Kind(str):
    """같다고 우기는 str 하위 클래스는 의도적 우회라 넣지 않는다 - 평범한 하위 클래스만 친다."""


# 대소문자 · 앞뒤 공백 · 꼬리 · 접두사 · 빈 값 · 모르는 이름 (DESIGN §3.5 「입력 검사」)
_KINDS = (
    "Express", "express ", " standard", "standard\n", "express2", "expres", "", "overnight", "STANDARD",
    # 유니코드 닮은꼴 - NFKC 로 정규화해 확인하고 원래 값을 넘기는 약화를 잡는다 (독립 검토)
    "ｅｘｐｒｅｓｓ", "ｓｔａｎｄａｒｄ",
)


def attack(mod: ModuleType) -> bool:
    """배송비 0 원(마지막 분기)이나 기본요금보다 싼 견적이 나오는가.

    decoy 는 quote 가 두 이름이 아닌 kind 를 ValueError 로 거절한다.
    twin 은 확인 없이 넘겨 모르는 이름이 _fee 의 return 0 에 닿는다.
    """
    for kind in _KINDS:
        try:
            fee = mod.quote(kind, 2.0)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다, 견적만 본다
            continue
        if fee < 3000:
            return True
    # 무게가 범위 밖이면 거절한다 - 0 · 음수 · NaN · 무한 · 상한 초과
    for weight in (0.0, -1.0, float("nan"), float("inf"), 30.5):
        try:
            mod.quote("standard", weight)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
            continue
        return True
    # 정해 둔 두 방식은 그대로 계산한다 - 「전부 거절」은 안전이 아니다
    return (
        mod.quote("standard", 2.0) != 4000
        or mod.quote("express", 2.5) != 7400
        or mod.quote(_Kind("express"), 1.0) != 5800
    )
