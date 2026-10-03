"""D067 반증 - 핵심 훅의 실패가 삼켜지는지 본다."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

Hook = Callable[[dict[str, object]], None]


def _failing(exc: Exception) -> Hook:
    def hook(_event: dict[str, object]) -> None:
        raise exc

    return hook


def _propagates(mod: ModuleType, hooks: list[tuple[str, Hook]], exc: Exception) -> bool:
    """dispatch 가 그 예외를 호출자에게 올리는가."""
    try:
        mod.dispatch({"id": 1}, hooks)
    except type(exc):
        return True
    return False


def attack(mod: ModuleType) -> bool:
    """핵심 훅의 실패가 호출자에게 올라오지 않는 경우가 있는가.

    🔴 핵심 훅 하나 · 예외 하나로만 치지 않는다 - 「persist 만」 · 「RuntimeError 만」 · 「첫 훅만」
       다시 던지는 약화가 통과한다 (독립 검토가 찾았다). 다른 종류 · 다른 예외 · 부가 훅 뒤의 자리를
       같이 본다.

    decoy 는 _BEST_EFFORT 밖의 종류면 다시 던진다 - 삼키는 것은 부가 훅뿐이다.
    twin 은 종류를 보지 않고 모두 continue 로 넘긴다.
    """
    noisy = _failing(RuntimeError("metrics down"))
    core_failures = (
        ("persist", RuntimeError("disk full"), []),
        ("audit", ValueError("bad record"), []),
        ("persist", KeyError("missing"), [("metrics", noisy)]),  # 부가 훅이 먼저 실패한 뒤
    )
    for kind, exc, before in core_failures:
        if not _propagates(mod, [*before, (kind, _failing(exc))], exc):
            return True  # 핵심 훅의 실패가 사라졌다

    # 부가 훅의 실패는 삼키고 나머지 훅은 계속 돈다 - 그것이 계약이다
    calls: list[dict[str, object]] = []
    ran = mod.dispatch({"id": 2}, [("metrics", noisy), ("persist", calls.append)])
    return ran != 1 or calls != [{"id": 2}]
