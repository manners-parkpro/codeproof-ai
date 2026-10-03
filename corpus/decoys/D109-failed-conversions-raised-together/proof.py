"""D109 반증 - 실패하는 파일의 수 · 위치 · 예외 종류를 바꿔 가며 올라온 예외를 본다."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType


class _Corrupt(Exception):
    """사용자 정의 Exception - 표준 예외 몇 개만 받는 약화를 드러낸다."""


# 파일마다 다른 종류의 실패 - 표준 · OSError 계열 · 사용자 정의 · 그룹 자체 · 인자가 많은 예외
_MAKERS: list[Callable[[], Exception]] = [
    lambda: ValueError("열 수가 다르다"),
    lambda: FileNotFoundError("없는 파일"),
    lambda: _Corrupt("깨진 머리"),
    lambda: ExceptionGroup("안쪽 실패", [KeyError("칸")]),
    lambda: UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
]
# 실패하는 파일의 위치 - 없음 · 처음 · 가운데 · 끝 · 여럿 · 전부
_PATTERNS: list[tuple[int, ...]] = [(), (0,), (2,), (4,), (0, 2, 4), (0, 1, 2, 3, 4)]
# 경로를 넘기는 모양 - 목록 · 한 번만 돌 수 있는 반복자
_FEEDS: list[Callable[[list[str]], object]] = [list, iter]
# 같은 종류의 실패가 많은 일괄 - 타입 · 메시지로 합치거나 열 건에서 자르는 약화는 서로 다른 다섯 실패로는 안 보인다
_BULK = 25
_BULK_PROBE = True


def _wrong(mod: ModuleType, pattern: tuple[int, ...], feed: Callable[[list[str]], object]) -> bool:
    paths = [f"file-{n}.csv" for n in range(len(_MAKERS))]
    raised = {paths[i]: _MAKERS[i]() for i in pattern}  # 패턴마다 새 예외 객체
    tried: list[str] = []

    def convert(path: str) -> None:
        tried.append(path)
        if path in raised:
            raise raised[path]

    try:
        mod.convert_all(convert, feed(paths))
    except ExceptionGroup as group:
        got = list(group.exceptions)
        if len(got) != len(raised) or any(not any(g is r for g in got) for r in raised.values()):
            return True
    else:
        if raised:  # 실패를 조용히 버렸다
            return True
    return tried != paths  # 한 파일의 실패가 나머지를 멈추지 않는다


def attack(mod: ModuleType) -> bool:
    """실패가 버려지거나 · 다른 객체로 바뀌거나 · 나머지 파일이 시도되지 않는 경우가 있는가.

    🔴 실패의 수를 하나만 쓰지 않는다 - 첫 실패만 담는 약화는 실패가 하나일 때 정답과 같다. 같은 타입 · 메시지의
       실패가 열셋인 일괄도 친다 - 중복을 합치거나 열 건에서 자르는 약화는 서로 다른 다섯 실패로는 안 보인다.
    🔴 그룹에 든 것이 convert 가 던진 바로 그 객체인지 본다 - 같은 메시지로 새로 만든 예외는 트레이스백을 잃는다.
    🔴 그룹이 아닌 예외가 그대로 올라오면(ExceptionGroup 밖으로 새면) attack 밖으로 나가 깨짐으로 센다.

    decoy 는 _convert_one 이 돌려준 예외를 convert_all 이 모두 모아 반복이 끝난 뒤 ExceptionGroup 으로 올린다.
    twin 은 모은 실패를 올리지 않아 convert_all 이 조용히 돌아온다.
    """
    if any(_wrong(mod, pattern, feed) for pattern in _PATTERNS for feed in _FEEDS):
        return True
    return _BULK_PROBE and _bulk(mod)


def _bulk(mod: ModuleType) -> bool:
    """파일 25개 중 13개가 타입 · 메시지는 같고 객체는 다른 예외로 실패한다 - 중복을 합치거나 개수에 상한을 두는 약화."""
    paths = [f"bulk-{n}.csv" for n in range(_BULK)]
    raised = {paths[n]: ValueError("열 수가 다르다") for n in range(0, _BULK, 2)}
    tried: list[str] = []

    def convert(path: str) -> None:
        tried.append(path)
        if path in raised:
            raise raised[path]

    try:
        mod.convert_all(convert, paths)
    except ExceptionGroup as group:
        got = list(group.exceptions)
        if len(got) != len(raised) or any(not any(g is r for g in got) for r in raised.values()):
            return True
    else:
        return True
    return tried != paths
