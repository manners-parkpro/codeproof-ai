"""D116 반증 - 시간대가 없는 시각과 있는 시각을 여러 서버 시간대에서 저장해 본다."""

from __future__ import annotations

import contextlib
import datetime
import os
import time
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

from codeproof_ai.corpus.proof import load_module

# tzdata 없이 libc 가 읽는 POSIX TZ 문자열 - UTC · UTC 보다 앞 · 서머타임이 있는 뒤 · 서머타임이 있는 앞
_ZONES = ["UTC0", "KST-9", "EST+5EDT,M3.2.0,M11.1.0", "NZST-12NZDT,M9.5.0,M4.1.0/3"]


class _NoOffset(datetime.tzinfo):
    """tzinfo 는 달렸지만 utcoffset 이 None 이다 - datetime 문서는 이런 시각도 naive 로 정의한다."""

    def utcoffset(self, dt: datetime.datetime | None) -> None:
        return None

    def dst(self, dt: datetime.datetime | None) -> None:
        return None

    def tzname(self, dt: datetime.datetime | None) -> None:
        return None


# 시간대가 없는 시각 - 평범한 시각 · 서머타임 틈 · 서머타임 겹침(fold) · utcoffset 이 None 인 tzinfo
_NAIVE = [
    datetime.datetime(2026, 10, 3, 9, 30),
    datetime.datetime(2026, 3, 8, 2, 30),
    datetime.datetime(2026, 11, 1, 1, 30, fold=1),
    datetime.datetime(2026, 10, 3, 9, 30, tzinfo=_NoOffset()),
]
# 시간대가 있는 시각 - UTC · 정시 오프셋 · 30분 단위 음의 오프셋 · 45분 단위 오프셋
_AWARE = [
    datetime.datetime(2026, 10, 3, 9, 30, tzinfo=datetime.UTC),
    datetime.datetime(2026, 10, 3, 18, 30, tzinfo=datetime.timezone(datetime.timedelta(hours=9))),
    datetime.datetime(2026, 10, 3, 5, 0, tzinfo=datetime.timezone(-datetime.timedelta(hours=4, minutes=30))),
    datetime.datetime(2026, 10, 3, 23, 15, tzinfo=datetime.timezone(datetime.timedelta(hours=12, minutes=45))),
]


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


def _utc(when: datetime.datetime) -> str:
    """그 순간의 UTC 표기 - 오프셋을 직접 빼서 구한다."""
    offset = when.utcoffset()
    assert offset is not None
    return (when.replace(tzinfo=None) - offset).replace(tzinfo=datetime.UTC).isoformat()


def attack(mod: ModuleType) -> bool:
    """시간대가 없는 시각의 결과가 서버 시간대마다 다르거나, 시간대가 있는 시각이 그 순간의 UTC 표기가 아닌가.

    🔴 서버 시간대를 바꿔 가며 친다 - 시간대 없는 시각을 지역 시각으로 해석하는 결함은 시간대가 UTC 인 기계(CI)
       하나에서는 드러나지 않는다.
    🔴 시간대 없는 시각을 거절하든 서버와 무관한 규칙(예: UTC 로 간주)으로 받든 묻지 않는다 - 주장은 서버의 지역
       시각으로 해석하지 않는다는 것이다.
    🔴 tzinfo 가 달렸어도 utcoffset 이 None 이면 naive 다 - tzinfo 만 보는 확인이 빠지지 않게.
    🔴 시간대마다 모듈을 다시 읽는다 - 모듈을 읽은 뒤에 TZ 만 바꾸면 import 때 지역 시간대를 읽어 naive 시각에
       붙이는 약화가 어느 호스트에서도 「시간대마다 같은 결과」로 지나간다 (4라운드 검토).

    decoy 는 _aware 가 tzinfo 가 없거나 utcoffset 이 None 인 시각을 astimezone 전에 거절한다.
    twin 은 확인이 없어 astimezone 이 시간대 없는 시각을 서버의 지역 시각으로 해석한다.
    """
    outcomes: list[set[str]] = [set() for _ in _NAIVE]
    zones = _ZONES if hasattr(time, "tzset") else [None]  # Windows - 지금 시간대 하나로만 친다
    for n, spec in enumerate(zones):
        with _zone(spec) if spec else contextlib.nullcontext():
            if spec == "KST-9" and time.localtime(0).tm_hour != 9:
                msg = "TZ 를 바꿀 수 없는 환경이다 - 시간대 축을 칠 수 없다"
                raise RuntimeError(msg)
            # 그 시간대에서 모듈을 다시 읽는다 - import 때 지역 시간대를 읽어 두는 약화가 빠지지 않게
            zoned = load_module(Path(str(mod.__file__)), f"{mod.__name__}_zone{n}") if spec else mod
            for seen, when in zip(outcomes, _NAIVE, strict=True):
                try:
                    seen.add(zoned.to_storage(when))
                except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
                    seen.add("<거절>")
            if any(zoned.to_storage(when) != _utc(when) for when in _AWARE):
                return True
    return any(len(seen) > 1 for seen in outcomes)
