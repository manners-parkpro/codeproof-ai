"""D028 반증 - 커서가 닫히는지 본다."""

from __future__ import annotations

from types import ModuleType


class _Cursor:
    def __init__(self) -> None:
        self.closed = False
        self.rows: list[str] = []

    def execute(self, sql: str, params: tuple[str, ...]) -> object:
        self.rows.append(params[0])
        return None

    def close(self) -> None:
        self.closed = True


def attack(mod: ModuleType) -> bool:
    """store 가 끝난 뒤 커서가 열린 채 남는가.

    decoy 는 closing 이 정상 경로에서도 예외 경로에서도 닫는다.
    twin 은 둘 다 열어 둔 채 빠져나간다.
    """
    made: list[_Cursor] = []

    def make() -> _Cursor:
        c = _Cursor()
        made.append(c)
        return c

    if mod.store(make, ["a", "b"]) != 2:
        return True
    if not made[-1].closed:
        return True  # 정상 경로에서 샜다

    def exploding() -> object:
        yield "ok"
        raise RuntimeError("row source failed")

    try:
        mod.store(make, exploding())
    except RuntimeError:
        pass
    return not made[-1].closed  # 예외 경로에서 샜는가
