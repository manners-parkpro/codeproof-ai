"""D024 반증 - 원래 예외가 정리 예외에 가려지는지, 성공했을 때 정리 실패가 감춰지는지 본다."""

from __future__ import annotations

from types import ModuleType


class _Custom(Exception):
    pass


_CLOSE_FAILURES = (RuntimeError, OSError, ValueError, TypeError, _Custom)


def _bad(exc_type: type[Exception], box: list[BaseException]) -> object:
    class _H:
        def close(self) -> None:
            exc = exc_type("close failed")
            box.append(exc)
            raise exc
    return _H()


def attack(mod: ModuleType) -> bool:
    """work 가 실패하면 그 예외가, 성공하면 정리 실패가 그대로(같은 객체) 호출자에게 가는가.

    decoy 는 실패 경로에서 정리 실패를 삼키고 성공 경로에서는 올린다. twin 은 실패 경로에서도 올려 원래 예외를 가린다.
    🔴 정리 실패를 여러 Exception 타입으로 낸다 - except 를 좁힌 약화가 RuntimeError 하나로는 지나갔다 (독립 검토).
       「그대로」는 같은 객체다 - 새 예외로 감싸 올리는 약화가 타입만 보면 지나갔다. BaseException 은 주장 밖이다.
    """
    for exc_type in _CLOSE_FAILURES:
        # 절 A: work 의 예외가 그대로 (같은 객체)
        raised = ValueError("real error")

        def work() -> object:
            raise raised
        try:
            mod.run([_bad(exc_type, []), _bad(exc_type, [])], work)
        except BaseException as got:  # noqa: BLE001
            if got is not raised:
                return True
        else:
            return True
        # 절 B: work 가 성공하면 정리 실패가 그대로 (같은 객체)
        box: list[BaseException] = []
        try:
            mod.run([_bad(exc_type, box)], lambda: 42)
        except BaseException as got:  # noqa: BLE001
            if not box or got is not box[0]:
                return True
        else:
            return True
    closed: list[str] = []

    class _Ok:
        def close(self) -> None:
            closed.append("x")
    return mod.run([_Ok()], lambda: 42) != 42 or closed != ["x"]
