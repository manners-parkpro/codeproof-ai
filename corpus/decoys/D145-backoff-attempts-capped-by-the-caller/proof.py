"""D145 반증 - 상한 안팎의 attempts · base 로 대기 목록을 받아 길이 · 값 · 거절을 본다."""

from __future__ import annotations

import enum
import math
from types import ModuleType


class _Times(enum.IntEnum):
    ZERO = 0
    THREE = 3
    TEN = 10
    ELEVEN = 11


class _Count(int):
    """메서드를 재정의하지 않은 int 하위 클래스."""


class _Secs(float):
    """메서드를 재정의하지 않은 float 하위 클래스."""


_GOOD_ATTEMPTS = [*range(1, 11), _Times.THREE, _Times.TEN, _Count(7)]
_GOOD_BASES = [0.001, 0.5, 1, 1.0, 59.999, 60, 60.0, 5e-324, 1e-300, _Secs(2.5), _Count(3)]
_BAD_ATTEMPTS = [0, -1, 11, 12, 50, 10**6, True, False, -(10**30), _Times.ZERO, _Times.ELEVEN, _Count(11)]
_BAD_BASES = [0, 0.0, -0.0, -1.0, math.nextafter(60.0, math.inf), 60.000001, 61, float("inf"), float("-inf"), float("nan"), 1e308, _Secs(60.5)]


def attack(mod: ModuleType) -> bool:
    """받아들일 요청의 목록이 base × 2**n 차례가 아니거나 길이가 다르거나, 상한 밖의 요청을 받는가.

    🔴 attempts 는 한 칸 넘는 값부터 아주 큰 값까지 친다 - 상한 근처만 치면 「상한 두 배까지」 같은 약화가 빠진다.
    🔴 base 는 NaN · 무한대 · 아주 큰 유한 수를 친다 - 비교를 거꾸로 쓴 확인은 NaN 을 지나보낸다.
    🔴 횟수는 1~10 전부와 IntEnum · int 하위 클래스로 친다 - 가운데 값 하나를 빠뜨리거나 하위 타입이면 상한을 건너뛰는 판이
       빠지지 않게. bool 횟수(True · False)는 거절한다. base 는 float · int 하위 클래스와 60 바로 위(nextafter)까지 친다.
    🔴 거절 방식은 묻지 않는다.

    decoy 는 backoff 가 attempts 와 base 를 확인한 뒤에만 _delays 를 부른다.
    twin 은 attempts 를 확인하지 않아 1000 에 천 개짜리 목록을 만든다.
    """
    for attempts in _GOOD_ATTEMPTS:
        for base in _GOOD_BASES:
            try:
                got = mod.backoff(base, attempts)
            except Exception:  # noqa: BLE001 - 받아들일 요청을 거절하면 깨진 것이다
                return True
            if got != [base * 2**n for n in range(int(attempts))] or len(got) > 10 or any(d > 30720 for d in got):
                return True
    for attempts in _BAD_ATTEMPTS:
        for base in (1.0, 0.5):
            try:
                mod.backoff(base, attempts)
            except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                continue
            return True
    for base in _BAD_BASES:
        for attempts in (1, 10):
            try:
                mod.backoff(base, attempts)
            except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
                continue
            return True
    return False
