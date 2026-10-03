"""D089 반증 - 정의되지 않은 변의 길이로 큰 할당을 요청하게 만든다."""

from __future__ import annotations

from types import ModuleType

_CAP = 64 * 64 * 4
# 정의된 값의 앞뒤 · 0 · 음수 · 아주 큰 값 · 같은 값의 다른 타입 (DESIGN §3.5 「크기 · 범위」)
# 🔴 큰 음수도 친다 - 위로만 자르는 약화(min(side, 64))는 음수를 통과시키고 제곱이 상한을 넘긴다
_PROBES: tuple[object, ...] = (0, 1, 15, 17, 63, 65, -16, -64, -65, -(10**6), 128, 10**6, 2**31, 64.5, "64", True)


def attack(mod: ModuleType) -> bool:
    """정의된 값이 아닌 side 가 상한보다 큰 바이트열 요청에 닿는가.

    🔴 실제로 할당하지 않는다 - 모듈의 bytes 를 요청 크기만 적는 대리로 바꿔 본다. 호스트 메모리에
       기대면 성패가 환경에 따라 달라진다 (D061 · D075 와 같은 이유).

    decoy 는 Side(side) 가 16 · 64 가 아닌 값을 ValueError 로 거절한다.
    twin 은 side 를 그대로 크기로 써 상한보다 큰 할당을 요청한다.
    """
    asked: list[int] = []

    def spy(size: int) -> bytes:
        asked.append(size)
        return b""

    mod.bytes = spy  # type: ignore[attr-defined]
    try:
        # 🔴 고정 탐침만 치면 열거형에 멤버를 더해 허용 목록을 넓힌 약화(96 · 256)나 IntFlag 조합값(80)이 빠진다 -
        #    정수 구간 전체와 열거형 멤버 전부를 친다 (독립 검토)
        for side in (*_PROBES, *range(-300, 301), *list(mod.Side)):
            try:
                mod.blank_tile(side)
            except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다, 요청된 크기만 본다
                pass
    finally:
        del mod.bytes
    if any(size > _CAP or size < 0 for size in asked):
        return True

    # 정의된 두 값은 그대로 만들어진다 - 「전부 거절」은 안전이 아니다
    return mod.blank_tile(16) != bytes(16 * 16 * 4) or mod.blank_tile(64) != bytes(_CAP)
