"""D026 반증 - 형태가 다른 입력을 첨자 접근에 밀어 넣는다."""

from __future__ import annotations

from types import ModuleType

_MALFORMED = (
    None,
    42,
    "kind",
    [],
    {},
    {"other": "x"},
    {"kind": 7},
)


def attack(mod: ModuleType) -> bool:
    """TypeGuard 를 통과하지 못한 값이 본문에 도달하는가.

    decoy 는 is_envelope 가 "dropped" 로 걷어낸다.
    twin 은 검사가 없어 TypeError · KeyError · AttributeError 로 터진다.
    """
    for value in _MALFORMED:
        try:
            got = mod.route(value)
        except Exception:
            return True  # 본문에 도달해 터졌다
        if got != "dropped":
            return True  # 걸러졌어야 할 값이 처리됐다
    # 정상 입력이 망가지지 않았는지도 본다
    return mod.route({"kind": "ping"}) != "PING"
