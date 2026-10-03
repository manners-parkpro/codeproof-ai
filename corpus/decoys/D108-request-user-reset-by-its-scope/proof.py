"""D108 반증 - 요청을 처리한 뒤(정상 · 예외 · 중첩) 요청 사용자 변수를 본다."""

from __future__ import annotations

import contextvars
from types import ModuleType


class _Stop(BaseException):
    """사용자 정의 BaseException - 이름을 늘어놓아 받는 복원이 놓친다."""


# 부르기 전 값 - 기본값 · 다른 사용자. 기본값에서만 시작하면 「기본값으로 되돌리는」 약화가 안 보인다 (D094)
_STARTS: list[str | None] = [None, "admin"]
# 한 번도 set 되지 않은 시작 상태도 친다 - token.old_value 로 되돌리는 약화는 거기에 Token.MISSING 을 남긴다
_UNSET_START = True
# action 이 던지는 동기 예외 - Exception · BaseException 의 표준 셋 · 사용자 정의
_FAILURES: list[BaseException] = [ValueError("요청 실패"), KeyboardInterrupt(), SystemExit(1), _Stop()]


def _leaks(mod: ModuleType, var: contextvars.ContextVar[str | None], start: str | None) -> bool:
    seen: list[str | None] = []
    mod.handle("kim", lambda: seen.append(var.get()))
    if seen != ["kim"] or var.get() != start:
        return True
    for failure in _FAILURES:

        def fail(failure: BaseException = failure) -> None:
            raise failure

        try:
            mod.handle("lee", fail)
        except BaseException:  # noqa: BLE001, S110 - 예외가 어떻게 올라오는지는 묻지 않는다
            pass
        if var.get() != start:
            return True
    return False


def _nested_leaks(mod: ModuleType, var: contextvars.ContextVar[str | None], start: str | None) -> bool:
    """안쪽 handle 은 바깥 사용자를 시작 값으로 갖는다 - 끝나면 바깥 사용자로, 바깥이 끝나면 처음 값으로."""
    inner: list[str | None] = []

    def outer() -> None:
        mod.handle("inner", lambda: inner.append(var.get()))
        inner.append(var.get())

    mod.handle("outer", outer)
    return inner != ["inner", "outer"] or var.get() != start


_PROBES = [_leaks, _nested_leaks]


def attack(mod: ModuleType) -> bool:
    """handle 이 끝난 뒤(정상 반환 · 동기 예외 · 중첩) _request_user 가 부르기 전 값이 아닌가.

    🔴 action 안에서는 넘긴 사용자가 보여야 한다 - 사용자를 아예 넣지 않는 것은 안전이 아니다.
    🔴 예외가 올라오는 방식은 묻지 않는다. 주장은 변수의 값만 말한다.

    decoy 는 _request_scope 가 들어올 때 받은 토큰으로 finally 에서 reset 해 set 이전 값으로 되돌린다.
    twin 은 _request_scope 가 아무것도 되돌리지 않아 handle 이 넣은 사용자가 그대로 남는다.
    """
    var = mod._request_user
    # 이 문맥에서 한 번도 set 되지 않은 상태 - 가장 흔한 시작이다. 새 Context 안에서 돌리고 기본값과 견준다
    if _UNSET_START and contextvars.Context().run(lambda: any(probe(mod, var, var.get()) for probe in _PROBES)):
        return True
    for start in _STARTS:
        token = var.set(start)
        try:
            if any(probe(mod, var, start) for probe in _PROBES):
                return True
        finally:
            var.reset(token)
    return False
