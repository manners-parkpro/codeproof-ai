"""D120 반증 - 여러 길이 · 여러 타입의 데이터를 여러 크기로 나눠 표준 라이브러리의 나누기와 견준다."""

from __future__ import annotations

import enum
import itertools
from types import ModuleType

class _Size(enum.IntEnum):
    THREE = 3
    ZERO = 0
    MINUS = -2


class _Int(int):
    """메서드를 재정의하지 않은 int 하위 클래스 - 위협 모델 안이다."""


# 나눌 데이터 - 빈 것 · 하나 · 크기의 배수 · 배수 아님 · 문자열(공백 · 줄바꿈 · 탭 포함) · 튜플
_DATA: list[object] = [
    [],
    ["a"],
    [f"x{n}" for n in range(12)],
    [f"y{n}" for n in range(13)],
    "abcdefghij",
    "ab cd\nef\tgh  i j",
    "",
    tuple(f"t{n}" for n in range(7)),
]
# 받아들일 크기 - 1 · 2 · 3 · 데이터보다 큼 · 아주 큼(sys.maxsize 너머 포함) · bool(True 는 1) · IntEnum · int 하위 클래스
_SIZES = [1, 2, 3, 5, 12, 13, 14, 10**9, 2**63, 10**30, True, _Size.THREE, _Int(4)]
# 거절할 크기 - 0 · 음수 · bool(False 는 0) · IntEnum · int 하위 클래스
_REJECTED = [0, -1, -3, -(10**9), -(2**63), False, _Size.ZERO, _Size.MINUS, _Int(0), _Int(-5)]


def attack(mod: ModuleType) -> bool:
    """조각이 앞에서부터 size 개씩 겹침도 빠짐도 없이 나눈 것이 아니거나, 1 보다 작은 size 를 받는가.

    🔴 기대값은 itertools.batched 로 따로 만든다 - decoy 와 같은 식으로 만들면 무엇이든 통과한다.
    🔴 크기의 배수가 아닌 길이를 친다 - 배수만 치면 「마지막 짧은 조각을 버리는」 약화가 빠진다.
    🔴 조각의 타입은 묻지 않는다 - 주장은 내용만 말한다 (튜플로 돌려줘도 같다).
    🔴 거절 방식은 묻지 않는다 - 어떤 예외든 거절이다. 음수 크기는 range 가 조용히 빈 목록을 만들 수 있어 따로 친다.
    🔴 sys.maxsize 너머의 크기 · IntEnum · int 하위 클래스 · 공백이 든 문자열을 친다 (쓰는 단계 점검) - islice 로 꺼내는 판 ·
       정확히 int 일 때만 확인하는 판 · textwrap 으로 나누는 판이 빠지지 않게.

    decoy 는 반열린 조각 data[start : start + size] 를 size 걸음으로 이어 붙여 빈틈도 겹침도 없다.
    twin 은 끝을 하나 덜 잡아 조각마다 마지막 항목이 빠진다.
    """
    for data in _DATA:
        for size in _SIZES:
            got = [tuple(chunk) for chunk in mod.chunks(data, size)]
            # batched 는 크기만큼 버퍼를 먼저 잡는다 - 길이보다 큰 크기는 길이로 줄여도 나누는 결과가 같다
            if got != list(itertools.batched(data, min(size, max(len(data), 1)))):
                return True
    # 🔴 거절 절도 어떤 data 든이다 - 한 데이터로만 치면 확인 앞의 「빈 data 빠른 길」이 지나간다 (독립 검토)
    for size, data in itertools.product(_REJECTED, _DATA):
        try:
            mod.chunks(data, size)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    return False
