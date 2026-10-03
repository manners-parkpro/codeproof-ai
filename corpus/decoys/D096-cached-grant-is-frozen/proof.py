"""D096 반증 - 캐시가 돌려준 객체를 고쳐 다음 호출을 오염시킨다."""

from __future__ import annotations

from types import ModuleType


def _poison_attempts(grant: object) -> None:
    """평범한 코드가 쓸 법한 변경을 전부 시도한다 - 실패는 삼킨다.

    🔴 __dict__ 직접 쓰기 · object.__setattr__ 는 넣지 않는다 - 불변을 일부러 우회하는 경로이고 주장 밖이다
       (1라운드 검토의 위협 모델과 같다).
    """
    steps = (
        lambda: grant.roles.add("admin"),  # type: ignore[attr-defined]
        lambda: grant.roles.update({"admin"}),  # type: ignore[attr-defined]
        # 🔴 list 같은 다른 가변 컨테이너의 변경 수단도 친다 - frozen 은 두고 roles 만 list 로 둔 얕은 동결이
        #    이것으로만 드러난다 (독립 검토)
        lambda: grant.roles.append("admin"),  # type: ignore[attr-defined]
        lambda: grant.roles.extend(["admin"]),  # type: ignore[attr-defined]
        lambda: grant.roles.insert(0, "admin"),  # type: ignore[attr-defined]
        lambda: grant.roles.__setitem__(0, "admin"),  # type: ignore[attr-defined]
        lambda: setattr(grant, "roles", frozenset({"viewer", "admin"})),
    )
    for step in steps:
        try:
            step()
        except (AttributeError, TypeError, ValueError):
            pass
        except Exception:  # noqa: BLE001 - dataclasses.FrozenInstanceError 등 거절은 무엇이든 괜찮다
            pass


def attack(mod: ModuleType) -> bool:
    """받은 Grant 를 고친 뒤 같은 spec 의 다음 호출이 admin 을 허락하는가.

    decoy 는 frozen dataclass 와 frozenset 이라 대입도 제자리 변경도 거절된다.
    twin 은 일반 dataclass 와 set 이라 roles.add 가 캐시에 남은 객체를 바꾼다.
    """
    grant = mod.grant_for("viewer, editor")
    _poison_attempts(grant)
    if mod.grant_for("viewer, editor").allows("admin"):
        return True

    # 해석은 그대로다 - 공백 정리 · 빈 항목 무시 · spec 마다 따로
    if not mod.grant_for(" viewer ,, editor ").allows("editor") or mod.grant_for("viewer").allows("editor"):
        return True
    return set(mod.grant_for("viewer, editor").roles) != {"viewer", "editor"}
