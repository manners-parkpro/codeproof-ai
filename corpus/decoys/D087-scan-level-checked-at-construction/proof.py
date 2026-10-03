"""D087 반증 - 모르는 등급으로 아주 큰 업로드를 판정받는다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """크기 제한 없이 통과하는 요청을 만들 수 있는가.

    decoy 는 생성자가 모르는 등급을 거절해 마지막 분기에 닿지 못한다.
    twin 은 모르는 등급의 요청이 만들어져 크기와 상관없이 통과한다.
    """
    # 알려진 등급으로 시작하거나 공백이 붙은 값 - 앵커 없는 match · startswith · strip 약화를 잡는다
    for level in ("relaxed", "STRICT", "", "strict-x", "basic2", "strict "):
        try:
            request = mod.ScanRequest(level, 10**12)
        except ValueError:
            continue  # 의도한 거절
        if mod.accept(request):
            return True

    # 만든 뒤에 등급을 바꿀 수 없어야 한다 - frozen 이 빠지면 마지막 분기에 닿는다
    sneaky = mod.ScanRequest("strict", 10**12)
    try:
        sneaky.level = "relaxed"
    except AttributeError:  # FrozenInstanceError 는 AttributeError 다
        pass
    else:
        if mod.accept(sneaky):
            return True

    # 알려진 등급은 크기대로 판정된다
    if mod.accept(mod.ScanRequest("strict", 2_000_000)):
        return True
    return not mod.accept(mod.ScanRequest("basic", 2_000_000))
