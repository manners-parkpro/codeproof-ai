"""D106 반증 - 하루의 경계 초에 놓인 이벤트를 여러 날 · 여러 서버 시간대에서 센다."""

from __future__ import annotations

import contextlib
import datetime
import os
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

from codeproof_ai.corpus.proof import load_module, race_window

# 🔴 동시 탐침은 비결정적이다 - 양쪽 다 같은 횟수로 시도하므로 완화가 아니다.
ATTEMPTS = 3
_ADDS = 1000  # 그날 앞뒤로 더하는 수
_FAR = 40 * 86_400  # 더하는 이벤트를 그날에서 띄우는 거리

_DAY = 86_400
# 달 · 해의 경계 · 윤일과 윤년이 아닌 100년 · 1970 이전 · 먼 과거와 미래
_DAYS = [
    datetime.date(1970, 1, 1), datetime.date(1969, 12, 31), datetime.date(2000, 2, 28),
    datetime.date(2000, 2, 29), datetime.date(2000, 3, 1), datetime.date(2100, 3, 1),
    datetime.date(2024, 12, 31), datetime.date(2025, 1, 1), datetime.date(2026, 10, 3),
    datetime.date(1, 1, 1), datetime.date(9999, 12, 31),
]
# tzdata 없이 libc 가 읽는 POSIX TZ 문자열 - UTC · UTC 보다 앞 · 서머타임이 있는 뒤 · 서머타임이 있는 앞
_ZONES = ["UTC0", "KST-9", "EST+5EDT,M3.2.0,M11.1.0", "NZST-12NZDT,M9.5.0,M4.1.0/3"]
# 그날 0시에서 떨어진 초 - 0시 앞뒤 · 한낮 · 23:59:58 · 23:59:59 · 다음 날 0시
_OFFSETS = [-1, 0, 1, _DAY // 2, _DAY - 2, _DAY - 1, _DAY]
# 같은 날의 표현 - 날짜 · 시각이 붙은 datetime
_FORMS = [lambda day: day, lambda day: datetime.datetime(day.year, day.month, day.day, 15, 30)]


def _midnight(day: datetime.date) -> int:
    return int(datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.UTC).timestamp())


@contextlib.contextmanager
def _zone(spec: str) -> Iterator[None]:
    """프로세스 시간대를 잠시 바꾼다 - 원래 값(없음 포함)으로 되돌린다."""
    saved = os.environ.get("TZ")
    os.environ["TZ"] = spec
    time.tzset()
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = saved
        time.tzset()


def _miscounts(mod: ModuleType) -> bool:
    timeline = mod.Timeline()
    events: list[int] = []
    for day in _DAYS:
        s = _midnight(day)
        events += [s + offset for offset in _OFFSETS]
    events += [events[0]] * 3 + [events[-1]] * 2  # 같은 초에 여럿
    for when in reversed(events):  # 넣는 순서를 섞는다
        timeline.add(when)
    for day in _DAYS:
        s = _midnight(day)
        want = sum(1 for when in events if s <= when < s + _DAY)
        if any(timeline.count_on(form(day)) != want for form in _FORMS):
            return True
    return mod.Timeline().count_on(_DAYS[0]) != 0


def _torn(mod: ModuleType) -> bool:
    """세는 동안 다른 스레드가 그날 밖의 이벤트를 더해도 세는 값이 스레드를 띄우기 전과 같은가.

    절댓값이 아니라 띄우기 전 값과 견준다 - 날짜 계산 · 시간대 축은 _miscounts 가 보고, 여기서는 경쟁만 본다.
    창은 더하는 쪽에만 연다 - 세는 쪽까지 추적하면 느려져 두 bisect 사이에 끼어들 기회가 줄어든다 [실측 · 각 10회].
    """
    day = datetime.date(2026, 10, 3)
    s = _midnight(day)
    timeline = mod.Timeline()
    for offset in (0, 1, _DAY // 2, _DAY - 1):
        timeline.add(s + offset)
    before = timeline.count_on(day)
    changed: list[int] = []
    done = threading.Event()

    def count() -> None:
        while not done.is_set():
            got = timeline.count_on(day)
            if got != before:
                changed.append(got)

    def add() -> None:
        for k in range(_ADDS):
            # 그날에서 멀리 띄운다 - 경계 · 시간대 · 날짜 계산 축은 _miscounts 가 보고, 앞쪽 이벤트는 색인을 밀어 경쟁을 드러낸다
            timeline.add(s - _FAR - k)
            timeline.add(s + _FAR + k)
        done.set()

    with race_window("add"):
        threads = [threading.Thread(target=count), threading.Thread(target=add)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    return bool(changed)


def attack(mod: ModuleType) -> bool:
    """그날 0시 이상 다음 날 0시 미만의 이벤트 수와 count_on 이 다른 날 · 다른 서버 시간대가 있는가.

    🔴 경계 초를 양쪽 다 친다 - 그날 0시(넣어야 한다) · 23:59:59(넣어야 한다) · 다음 날 0시(빼야 한다).
       한쪽만 치면 반대쪽으로 한 칸 민 약화가 빠진다.
    🔴 서버 시간대를 바꿔 가며 친다. 0시를 서버의 지역 시각으로 잡는 약화는 시간대가 UTC 인 기계(CI)에서
       드러나지 않는다.
    🔴 날짜만이 아니라 시각이 붙은 datetime 도 넣는다 - 시각까지 epoch 초로 바꾸는 약화가 빠지지 않게.
    🔴 시간대마다 모듈을 다시 읽는다 - 모듈을 읽은 뒤에 TZ 만 바꾸면 import 때 지역 오프셋을 읽어 두는 약화가
       UTC 기계에서 드러나지 않는다 (4라운드 검토).
    🔴 세는 동안 다른 스레드가 그날 밖의 이벤트를 더한다 - 두 bisect 사이에 끼어든 insort 는 그날 수를 바꾼다.

    decoy 는 count_on 이 다음 날 0시를 끝(배타)으로 넘겨 _count_between 의 bisect_left 와 맞는다.
    twin 은 23:59:59 를 끝으로 넘겨 그 초의 이벤트를 빠뜨린다.
    """
    if _torn(mod):
        return True
    if not hasattr(time, "tzset"):  # Windows - 지금 시간대 하나로만 친다
        return _miscounts(mod)
    for n, spec in enumerate(_ZONES):
        with _zone(spec):
            if spec == "KST-9" and time.localtime(0).tm_hour != 9:
                msg = "TZ 를 바꿀 수 없는 환경이다 - 시간대 축을 칠 수 없다"
                raise RuntimeError(msg)
            # 그 시간대에서 모듈을 다시 읽는다 - import 때 지역 시간대를 읽어 두는 약화가 빠지지 않게
            zoned = load_module(Path(str(mod.__file__)), f"{mod.__name__}_zone{n}")
            if _miscounts(zoned):
                return True
    return False
