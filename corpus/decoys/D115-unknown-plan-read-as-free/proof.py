"""D115 반증 - 아는 · 모르는 · 닮은 요금제 이름과 표의 이름 · 값 전부로 무제한 분기에 닿는지 본다."""

from __future__ import annotations

from types import ModuleType

# 아는 이름 · 대소문자 · 앞뒤 공백 · 전각 · 모르는 이름 · 빈 값 · 이어 붙인 이름
_PLANS = [
    "free", "starter", "pro", "team", "Pro", "PRO", " pro", "pro ", "pro\n", "ｐｒｏ",
    "enterprise", "unlimited", "", "None", "premium", "team-pro", "pro.team",
]
_KNOWN = {"free": 100, "starter": 100, "pro": 10_000, "team": 10_000}
_UNKNOWN_IS_FREE = True


def _plans(mod: ModuleType) -> list[str]:
    """고정 탐침에 더해 표의 이름과 값 전부 - 표에 등급을 늘린 약화가 빠지지 않게 (D089)."""
    return [*_PLANS, *mod._TIERS, *mod._TIERS.values()]


def attack(mod: ModuleType) -> bool:
    """어떤 요금제 이름에서든 daily_quota 가 None(무제한)을 돌려주거나, 아는 요금제가 제 한도가 아닌가.

    🔴 거절은 무제한이 아니다 - 모르는 이름을 예외로 끝내는 것은 안전하므로 묻지 않는다.
    🔴 받았다면 표에 없는 이름은 free 한도여야 한다 - None 만 보면 모르는 이름을 pro 등급으로 읽는 약화 ·
       대소문자를 접어 표의 등급으로 읽는 약화가 빠진다 (4라운드 검토).

    decoy 는 _tier 가 표에 없는 이름을 "free" 로 읽고 표의 값이 "free" · "pro" 뿐이라 마지막 분기에 닿지 않는다.
    twin 의 _tier 는 표에 없는 이름을 그대로 돌려줘 오타 · 모르는 요금제가 무제한이 된다.
    """
    for plan in _plans(mod):
        try:
            quota = mod.daily_quota(plan)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        if quota is None:
            return True
        # 표에 없는 이름은 가장 낮은 한도다 - 무제한이 아니어도 더 높은 등급으로 빠지면 주장이 깨진다
        if _UNKNOWN_IS_FREE and plan not in mod._TIERS and quota != _KNOWN["free"]:
            return True
    return any(mod.daily_quota(plan) != quota for plan, quota in _KNOWN.items())
