"""D119 반증 - 여러 fmt 로 내보내며 exporter 에서 불린 메서드 이름을 전부 기록한다."""

from __future__ import annotations

import ast
import enum
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

_ALLOWED = {"to_csv", "to_json"}
_OWN = {"csv": "to_csv", "json": "to_json"}
_ROWS = [{"id": "1", "name": "kim"}]

# 표에 없는 fmt - 대소문자 · 공백 · 줄바꿈 · 전각 · 메서드 이름 그대로 · 다른 형식 · 위험한 이름 · 비공개 · 던더 · 빈 값
_UNKNOWN = [
    "CSV", "Json", " csv", "csv ", "csv\n", "ｃｓｖ", "to_csv", "to_json", "xml", "pickle", "to_pickle",
    "delete_all", "purge", "_secret", "__class__", "__init__", "__getattribute__", "",
]


class _Fmt(str):
    """메서드를 재정의하지 않은 str 하위 클래스 - 위협 모델 안이다."""


class _Kind(enum.StrEnum):
    CSV = "csv"
    JSON = "json"
    PURGE = "purge"


class _Recorder:
    """어떤 이름을 꺼내든 그 이름을 부를 때 기록하는 exporter - 던더 이름 · 어떤 인자 꼴의 호출도 기록한다."""

    def __init__(self) -> None:
        object.__setattr__(self, "called", [])

    def __getattribute__(self, name: str) -> object:
        calls = object.__getattribute__(self, "called")
        if name == "called":
            return calls

        def method(*args: object, **kwargs: object) -> str:
            calls.append(name)
            return name

        return method


class _Concrete:
    """위험한 메서드를 클래스에 실제로 가진 exporter - 클래스 속성을 보고 고르는 약화가 여기서 드러난다."""

    def __init__(self) -> None:
        self.called: list[str] = []

    def _hit(self, name: str) -> str:
        self.called.append(name)
        return name

    def to_csv(self, *args: object) -> str:
        return self._hit("to_csv")

    def to_json(self, *args: object) -> str:
        return self._hit("to_json")

    def delete_all(self, *args: object) -> str:
        return self._hit("delete_all")

    def purge(self, *args: object) -> str:
        return self._hit("purge")

    def _secret(self, *args: object) -> str:
        return self._hit("_secret")


def _calls(mod: ModuleType, fmt: str, exporter: object) -> list[str]:
    try:
        mod.export(exporter, fmt, list(_ROWS))
    except Exception:  # noqa: BLE001, S110 - 표에 없는 fmt 의 거절 방식은 묻지 않는다
        pass
    if isinstance(exporter, _Recorder):
        return list(object.__getattribute__(exporter, "called"))
    return list(exporter.called)  # type: ignore[attr-defined]


def _source_strings(mod: ModuleType) -> list[str]:
    """모듈 소스의 문자열 상수와 이름 전부, 그리고 그 소문자 · to_ 를 뗀 꼴 - 표의 이름 · 모양 · 만드는 방식을 묻지 않고 표의 키를 다 친다."""
    tree = ast.parse(Path(mod.__file__ or "").read_text(encoding="utf-8"))
    words = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    words |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    words |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    return sorted(words | {w.lower() for w in words} | {w.removeprefix("to_") for w in words})


def _global_strings(mod: ModuleType) -> list[str]:
    """모듈 전역의 매핑 키 · 값과 열거형 멤버의 이름 · 값 - 실행해서 만든 표의 키도 덮는다 (독립 검토)."""
    found: set[str] = set()
    for name, value in vars(mod).items():
        if name.startswith("__"):
            continue
        if isinstance(value, Mapping):
            found.update(x for pair in value.items() for x in pair if isinstance(x, str))
        elif isinstance(value, type) and issubclass(value, enum.Enum):
            found.update(x for member in value for x in (member.name, member.value) if isinstance(x, str))
    return sorted(found)


def attack(mod: ModuleType) -> bool:
    """csv · json 이 제 메서드 하나만 한 번 부르지 않거나, 다른 fmt 가 to_csv · to_json 말고 다른 메서드에 닿거나 두 번 이상 부르면 True.

    🔴 표를 모듈 속성 이름으로 찾지 않는다 - 표 이름을 바꾸거나 match 로 고르는 안전한 변형이 깨짐으로 세어진다.
       모듈 소스의 문자열 상수 전부를 fmt 로 쳐서 표의 키를 빠짐없이 덮는다 (D089 · D115 - 표에 위험한 이름을 더한 약화).
       리터럴이 아닌 키(StrEnum auto · 이름에서 만든 키 · 소문자로 접은 키)는 소스의 이름과 그 꼴, 모듈 전역의 매핑 · 열거형으로 덮는다
       (독립 검토) - 후보로만 쓰고 정답으로 쓰지 않는다.
    🔴 던더 이름 · 어떤 인자 꼴의 호출도 기록하고, 위험한 메서드를 실제로 가진 exporter 로도 친다.
    🔴 str 하위 클래스 · StrEnum 도 fmt 다 - 정확히 str 일 때만 표를 쓰는 약화가 빠지지 않게.
    🔴 표에 없는 fmt 는 거절하든 허용한 메서드로 보내든 묻지 않는다.

    decoy 는 export 가 _METHODS[fmt] 로 이름을 고르므로 _render 의 getattr 에는 표의 값만 닿는다.
    twin 은 표에 없는 fmt 를 이름으로 그대로 넘겨, 아무 메서드나 불린다.
    """
    plain = ["csv", "json", *_UNKNOWN, *_source_strings(mod), *_global_strings(mod)]
    fmts: list[str] = [*plain, *(_Fmt(f) for f in plain), *_Kind]
    for fmt in fmts:
        for exporter in (_Recorder(), _Concrete()):
            called = _calls(mod, fmt, exporter)
            own = _OWN.get(str(fmt))
            if own is not None:
                if called != [own]:
                    return True
            elif len(called) > 1 or not set(called) <= _ALLOWED:
                return True
    return False
