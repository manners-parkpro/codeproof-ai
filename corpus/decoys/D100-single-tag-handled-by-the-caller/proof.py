"""D100 반증 - 태그 문자열 하나를 넘겨 글자로 쪼개지는지 본다."""

from __future__ import annotations

from types import ModuleType


class _Tag(str):
    """str 의 하위 클래스 - isinstance 는 걸러야 한다."""


def attack(mod: ModuleType) -> bool:
    """문자열 하나가 글자 단위로 쪼개지거나 바뀌어 표시되는가.

    한 글자 · 공백 · 쉼표가 든 태그 · 비ASCII · str 하위 클래스를 친다 - 한 글자 태그는 쪼개도 같아 보이므로
    그것만으로는 못 잡는다 (DESIGN §3.5 「입력 검사」 · 닮은꼴).

    decoy 는 label 이 문자열을 먼저 그대로 돌려준다. twin 은 문자열을 _joined 로 넘겨 sorted 가 글자로 쪼갠다.
    """
    # 🔴 주장의 첫 절(「_joined 에 닿는 값은 문자열이 아니다」)을 직접 잰다 - 출력만 보면 빈 문자열을 넘기는
    #    변이(tags and isinstance(...))는 결과가 같아 보이지 않는다 (독립 검토)
    reached: list[object] = []
    original = mod._joined

    def spy(tags: object) -> str:
        reached.append(tags)
        return original(tags)

    mod._joined = spy
    try:
        for tag in ("python", "a b", "x,y", "파이썬", _Tag("rust"), "zz", ""):
            if mod.label(tag) != tag:
                return True
    finally:
        mod._joined = original
    if any(isinstance(tags, str) for tags in reached):
        return True
    # 목록은 정렬해 잇는다 - 「전부 그대로」는 안전이 아니다
    return mod.label(["web", "api", "db"]) != "api, db, web" or mod.label([]) != ""
