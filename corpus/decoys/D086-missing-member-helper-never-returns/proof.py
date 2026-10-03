"""D086 반증 - 없는 회원의 메일 주소를 묻는다."""

from __future__ import annotations

from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """없는 회원에서 LookupError 가 아닌 결과가 나오는가.

    decoy 는 _missing 이 언제나 LookupError 를 던져 None 분기가 거기서 끝난다.
    twin 은 _missing 이 돌아와 None 의 .email 에서 AttributeError 가 난다.
    """
    mod._members["m1"] = mod.Member("Kim", "Kim@Example.com")
    if mod.email_of("m1") != "kim@example.com":
        return True
    try:
        mod.email_of("ghost")
    except LookupError:
        return False
    except Exception:  # noqa: BLE001 - 다른 예외가 곧 결함이다
        return True
    return True
