"""D111 반증 - 같은 체크를 여러 번 · 같은 값의 새 객체로 다시 보내고 기록 수를 센다."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable, Iterator
from types import ModuleType

_SESSION = 1001  # 작은 정수 캐시(-5~256) 밖이라 같은 값의 새 int 객체를 만들 수 있다


def _same(student: str, session: int) -> tuple[str, int]:
    return student, session


def _rebuilt(student: str, session: int) -> tuple[str, int]:
    """역직렬화한 재시도 - 값은 같고 객체는 새것이다."""
    return "".join(list(student)), int(str(session))


# 재시도가 인자를 넘기는 모양 - 같은 객체 · 같은 값의 새 객체
_RETRIES: list[Callable[[str, int], tuple[str, int]]] = [_same, _rebuilt]
_LATER = 2 * 86_400  # 재시도가 오는 시차(초) - 초 · 날짜 단위 시각도 바뀌게 하루를 넘긴다
_CLOCKS = ("time", "time_ns", "monotonic", "monotonic_ns")
_SHIFT_CLOCK = True


@contextlib.contextmanager
def _later() -> Iterator[None]:
    """재시도가 이틀 뒤에 온다 - time 의 시계를 민다 (date.today 도 time.time 을 따른다). 원래 함수로 되돌린다."""
    saved = {name: getattr(time, name) for name in _CLOCKS}
    time.time = lambda: saved["time"]() + _LATER
    time.time_ns = lambda: saved["time_ns"]() + _LATER * 10**9
    time.monotonic = lambda: saved["monotonic"]() + _LATER
    time.monotonic_ns = lambda: saved["monotonic_ns"]() + _LATER * 10**9
    try:
        yield
    finally:
        for name, clock in saved.items():
            setattr(time, name, clock)


def attack(mod: ModuleType) -> bool:
    """같은 체크를 다시 보내면 기록이 늘거나, 다른 학생 · 다른 회차의 체크가 하나로 합쳐지는가.

    🔴 재시도는 같은 객체만이 아니라 같은 값의 새 객체로도 온다 - 인자의 id 로 중복을 거르는 약화는 같은 객체의
       재시도만 치면 드러나지 않는다.
    🔴 재시도는 시간을 두고 온다 - 재시도 동안 시계를 이틀 민다. 마이크로초 안에 다시 부르기만 하면 초 · 날짜
       단위 시각이 기록에 낀 약화가 드러나지 않는다 (4라운드 검토).

    decoy 의 Check 는 frozen dataclass 라 필드 값으로 같고 해시가 같아 set.add 가 다시 온 체크를 더하지 않는다.
    twin 의 Check 는 보통 클래스라 객체마다 다르게 비교되어 재시도마다 기록이 하나씩 는다.
    """
    mod.check_in("kim", _SESSION)
    with _later() if _SHIFT_CLOCK else contextlib.nullcontext():
        for retry in _RETRIES:
            for _ in range(3):
                mod.check_in(*retry("kim", _SESSION))
    if len(mod._checks) != 1:
        return True

    # 다른 학생 · 다른 회차는 따로 남는다 - 「모두 하나로」는 안전이 아니다
    mod.check_in("lee", _SESSION)
    mod.check_in("kim", _SESSION + 1)
    if len(mod._checks) != 3:
        return True
    return not mod.checked_in("kim", _SESSION) or mod.checked_in("park", _SESSION)
