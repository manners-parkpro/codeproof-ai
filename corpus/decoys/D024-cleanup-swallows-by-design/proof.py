"""D024 반증 - 원래 예외가 정리 예외에 가려지는지 본다."""

from __future__ import annotations

from types import ModuleType


class _BadHandle:
    def close(self) -> None:
        raise RuntimeError("close failed")


def attack(mod: ModuleType) -> bool:
    """work 의 예외가 호출자에게 그대로 도달하는가.

    decoy 는 정리 실패를 삼켜 ValueError 가 보존된다.
    twin 은 정리 실패가 finally 밖으로 나가 원래 예외를 대체한다.
    """

    def work() -> object:
        raise ValueError("real error")

    try:
        mod.run([_BadHandle()], work)
    except ValueError:
        pass  # 원래 예외가 보존됐다
    except Exception:
        return True  # 정리 예외가 원래 예외를 가렸다
    else:
        return True  # 예외가 사라졌다 - 더 나쁘다

    # 정상 경로에서 정리가 실제로 도는지도 본다
    closed: list[str] = []

    class _Ok:
        def close(self) -> None:
            closed.append("x")

    if mod.run([_Ok()], lambda: 42) != 42:
        return True
    if closed != ["x"]:
        return True
    # 🔴 work 가 성공했을 때의 정리 실패는 감추지 않는다 (교차 패밀리 감사)
    try:
        mod.run([_BadHandle()], lambda: 42)
    except RuntimeError:
        return False
    return True
