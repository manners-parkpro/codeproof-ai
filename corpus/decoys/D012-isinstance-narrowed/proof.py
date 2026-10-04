"""D012 반증 - 바이너리 이벤트를 텍스트 경로로 밀어 넣는다."""

from __future__ import annotations

import dataclasses
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """BinaryEvent 가 .body 접근에 도달하는가.

    decoy 는 isinstance 분기가 먼저 걷어낸다.
    twin 은 그 분기가 없어 AttributeError 로 터진다.
    """
    binary = mod.BinaryEvent(payload=b"\x00\x01\x02")
    got = mod.summarize(binary)
    if got != "<binary 3B>":
        return True
    # 텍스트 경로의 정확성도 확인 - 가드가 정상 입력을 망치지 않았는지
    if mod.summarize(mod.TextEvent(body="  Hi  ")) != "hi":
        return True
    # 🔴 평범한 하위 클래스 (독립 검토) - type(event) is ... 로 좁히면 하위 클래스가 다른 쪽 줄로 간다
    class _Bin(mod.BinaryEvent):  # type: ignore[misc, name-defined]
        pass

    class _Txt(mod.TextEvent):  # type: ignore[misc, name-defined]
        pass

    @dataclasses.dataclass(frozen=True, slots=True)
    class _SlottedTxt(mod.TextEvent):  # type: ignore[misc, name-defined]
        pass

    if mod.summarize(_Bin(payload=b"abc")) != "<binary 3B>":
        return True
    for cls in (_Txt, _SlottedTxt):
        if mod.summarize(cls(body="  Hi  ")) != "hi":
            return True
    # 🔴 두 타입을 함께 상속한 하위 클래스 (교차 패밀리 감사 · 독립 검토) - 만들 수 있으면 MRO 가 고른 생성자가
    #    다른 쪽 필드를 채우지 않는다. 클래스 기본값은 slots 하위 클래스의 슬롯이 가린다
    for bases in (
        (mod.BinaryEvent, mod.TextEvent),
        (mod.TextEvent, mod.BinaryEvent),
        (mod.BinaryEvent, _SlottedTxt),
        (_SlottedTxt, mod.BinaryEvent),
        (_Bin, _Txt),
        (_Txt, _Bin),
    ):
        try:
            mixed = type("_Mixed", bases, {})
        except TypeError:
            continue  # 인스턴스 배치가 충돌해 그런 값은 만들 수 없다
        for kwargs in ({"payload": b"\x00"}, {"body": "  Hi  "}):
            try:
                event = mixed(**kwargs)
            except TypeError:
                continue  # 그 생성자가 받지 않는 인자
            try:
                mod.summarize(event)
            except AttributeError:
                return True
    return False
