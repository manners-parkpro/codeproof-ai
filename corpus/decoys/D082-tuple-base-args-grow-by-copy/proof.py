"""D082 반증 - 명령을 두 번 조립해 앞선 인자가 남는지 본다."""

from __future__ import annotations

from types import ModuleType

_BASE = ["tar", "--create", "--gzip"]


def attack(mod: ModuleType) -> bool:
    """두 번째 명령에 첫 번째 호출의 인자가 섞이거나 기본 인자가 바뀌는가.

    decoy 는 기본 인자가 튜플이라 += 가 새 튜플을 만들고 전역은 그대로다.
    twin 은 기본 인자가 리스트라 += 가 전역을 늘려 다음 명령에 쌓인다.
    """
    first = mod.command("a.tgz", ["docs"])
    second = mod.command("b.tgz", ["src", "-weird"])
    if first != [*_BASE, "--file", "a.tgz", "--", "docs"]:
        return True
    if second != [*_BASE, "--file", "b.tgz", "--", "src", "-weird"]:
        return True
    return list(mod._BASE_ARGS) != _BASE
