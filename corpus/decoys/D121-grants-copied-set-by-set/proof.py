"""D121 반증 - 내보낸 dict 와 안쪽 집합을 여러 변경 수단으로 고친 뒤 권한을 다시 본다."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

_GRANTS = [("kim", "read"), ("kim", "write"), ("lee", "read"), ("park", "admin"), ("park", "read"), ("park", "write")]


def _assign(d: dict[str, set[str]]) -> None:
    d["kim"] = {"admin"}


def _delete(d: dict[str, set[str]]) -> None:
    del d["lee"]


def _clear(d: dict[str, set[str]]) -> None:
    d.clear()


def _pop(d: dict[str, set[str]]) -> None:
    d.pop("park")


def _popitem(d: dict[str, set[str]]) -> None:
    d.popitem()


def _update(d: dict[str, set[str]]) -> None:
    d.update({"eve": {"admin"}})


def _setdefault(d: dict[str, set[str]]) -> None:
    d.setdefault("eve", set()).add("admin")


def _set_add(d: dict[str, set[str]]) -> None:
    d["lee"].add("admin")


def _set_discard(d: dict[str, set[str]]) -> None:
    d["kim"].discard("read")


def _set_clear(d: dict[str, set[str]]) -> None:
    d["park"].clear()


def _set_ior(d: dict[str, set[str]]) -> None:
    roles = d["lee"]
    roles |= {"admin"}


def _set_isub(d: dict[str, set[str]]) -> None:
    roles = d["park"]
    roles -= {"read"}


def _set_iand(d: dict[str, set[str]]) -> None:
    roles = d["park"]
    roles &= {"admin"}


def _set_pop(d: dict[str, set[str]]) -> None:
    d["kim"].pop()


# 변경 수단 - 바깥 dict: 대입 · 지우기 · 비우기 · pop · popitem · update · setdefault /
#             안쪽 집합: add · discard · clear · |= · -= · &= · pop
_EDITS: list[Callable[[dict[str, set[str]]], None]] = [
    _assign, _delete, _clear, _pop, _popitem, _update, _setdefault,
    _set_add, _set_discard, _set_clear, _set_ior, _set_isub, _set_iand, _set_pop,
]


def _fresh(mod: ModuleType) -> object:
    roles = mod.Roles()
    for user, role in _GRANTS:
        roles.grant(user, role)
    return roles


def _state(roles: object) -> dict[str, frozenset[str]]:
    return {user: roles.roles_of(user) for user in ("kim", "lee", "park", "eve")}  # type: ignore[attr-defined]


def attack(mod: ModuleType) -> bool:
    """export 가 grant 한 권한을 담지 않거나, 내보낸 값을 고친 뒤 roles_of · 다음 export 가 바뀌는가.

    🔴 변경 수단을 바깥 dict 와 안쪽 집합 모두에서 친다 - 바깥만 고치면 「바깥만 복사」 약화가 지나간다 (D093).
    🔴 내보낸 뒤에 grant 한 권한도 다음 export 에 나와야 한다 - 첫 사본을 캐시해 돌려주는 약화가 빠지지 않게.
    🔴 바꿀 수 없어 거절되는 것은 안전하다 - frozenset 이나 읽기 전용 보기로 돌려줘도 된다. 어떤 예외로 거절되든 묻지 않는다.

    decoy 는 _copied 가 바깥 dict 와 사용자마다의 집합을 새로 만들어 돌려준다.
    twin 은 바깥 dict 만 새로 만들고 안쪽 집합은 Roles 의 것을 그대로 담는다.
    """
    want = {"kim": {"read", "write"}, "lee": {"read"}, "park": {"admin", "read", "write"}}
    for edit in _EDITS:
        roles = _fresh(mod)
        before = _state(roles)
        exported = roles.export()  # type: ignore[attr-defined]
        if {user: set(r) for user, r in exported.items()} != want:
            return True
        try:
            edit(exported)
        except Exception:  # noqa: BLE001, S110 - 거절 방식은 묻지 않는다
            pass
        if _state(roles) != before:
            return True
        if {user: set(r) for user, r in roles.export().items()} != want:  # type: ignore[attr-defined]
            return True
        roles.grant("lee", "write")  # type: ignore[attr-defined]
        if set(roles.export()["lee"]) != {"read", "write"}:  # type: ignore[attr-defined]
            return True
    return _later_exports_broken(mod)


def _later_exports_broken(mod: ModuleType) -> bool:
    """쓰는 단계 점검이 찾은 양화 셋 - 시작 상태 · 나중 grant 의 새 사용자 · 몇 번째 export 든."""
    # 🔴 아무것도 grant 하지 않은 시작 상태에서 내보낸 값을 고쳐도 권한이 생기지 않는다
    for edit in _EDITS:
        empty = mod.Roles()
        try:
            edit(empty.export())
        except Exception:  # noqa: BLE001, S110 - 거절 방식은 묻지 않는다
            pass
        if any(empty.roles_of(u) for u in ("kim", "lee", "park", "eve")) or dict(empty.export()):
            return True
    # 🔴 앞선 export 뒤에 새 사용자에게 grant 한 권한도 다음 export 에 통째로 나온다
    roles = mod.Roles()
    roles.grant("kim", "read")
    roles.export()
    roles.grant("lee", "write")
    if {u: set(r) for u, r in roles.export().items()} != {"kim": {"read"}, "lee": {"write"}}:
        return True
    # 🔴 둘째 · 셋째 export 가 돌려준 값을 고쳐도 다음 export 와 roles_of 는 그대로다
    want = {"kim": {"read", "write"}, "lee": {"read"}, "park": {"admin", "read", "write"}}
    for edit in _EDITS:
        roles = _fresh(mod)
        before = _state(roles)
        for _ in range(3):
            try:
                edit(roles.export())  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001, S110
                pass
            if _state(roles) != before:
                return True
            if {u: set(r) for u, r in roles.export().items()} != want:  # type: ignore[attr-defined]
                return True
    return False
