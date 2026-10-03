"""D105 반증 - 형식 이름을 바꿔 가며 import_module 에 닿는 모듈 이름을 본다."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

from codeproof_ai.corpus.proof import load_module

_ALLOWED = {"json", "tomllib"}  # 주장의 두 이름
_REAL_IMPORT_MODULE = importlib.import_module

_FORMATS = [
    "json", "toml", "JSON", "Toml", " json", "json ", "json\n", "json\x00",
    "tomllib", "ｊｓｏｎ", "json.decoder", "json.tool", "toml.json", "../json",
    "os", "subprocess", "shutil", "__main__", "string", "", "yaml",
]


class _Parser:
    """import 한 모듈 자리에 둔다 - 실제 모듈을 import 하지 않는다."""

    def __init__(self, name: str) -> None:
        self.name = name

    def loads(self, text: str) -> tuple[str, str]:
        return self.name, text


def attack(mod: ModuleType) -> bool:
    """어떤 형식 이름에서든 import_module 이 정해 둔 두 이름 밖의 모듈을 받는가.

    🔴 거절은 안전하다 - 어떤 예외로 거절하든 묻지 않는다.
    🔴 진짜 importlib.import_module 자리에 감시자를 둔 채 모듈을 다시 읽는다 - mod.importlib 만 바꿔 끼우면
       import 꼴만 다른 안전한 판(from-import · 별칭)을 깨짐으로 거절한다 (4라운드 검토). 탐침 이름은 실제로
       import 되어도 해가 없는 것만 쓴다.
    🔴 표에 있는 이름의 다른 표현(대소문자 · 앞뒤 공백 · 전각 · 점으로 이은 하위 모듈)을 친다 - 정규화한 값으로
       확인하고 원래 값을 넘기는 약화는 「os」 같은 낯선 이름만으로는 드러나지 않는다.

    decoy 는 _parser_module 이 match 의 두 리터럴 중 하나일 때만 글자 그대로의 상수를 돌려주고 나머지는 거절한다.
    twin 은 맞지 않는 이름을 그대로 돌려줘 import_module 이 아무 모듈이나 import 한다.
    """
    asked: list[str] = []

    def import_module(name: str, package: str | None = None) -> _Parser:
        asked.append(name)
        return _Parser(name)

    importlib.import_module = import_module  # type: ignore[assignment]
    try:
        watched = load_module(Path(str(mod.__file__)), f"{mod.__name__}_watched")
        for fmt in _FORMATS:
            try:
                watched.parse(fmt, "{}")
            except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                continue
        if any(name not in _ALLOWED for name in asked):
            return True
        # 두 형식은 각자의 해석기로 간다 - 「전부 거절」은 안전이 아니다
        return watched.parse("json", "{}") != ("json", "{}") or watched.parse("toml", "a = 1") != ("tomllib", "a = 1")
    finally:
        importlib.import_module = _REAL_IMPORT_MODULE
