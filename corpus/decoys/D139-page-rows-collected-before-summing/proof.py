"""D139 반증 - 쪽마다 시도 계획(끝까지 · 도중에 끊김 · 부르자마자 끊김 · 다른 예외)을 정한 가짜 원천으로 합을 받아, 합 · 부른 횟수 ·
올라온 예외를 본다. 시간 초과가 아닌 예외는 일시 오류처럼 보이는 것(errno · 메시지 · 원인 사슬 · StopIteration)까지 친다."""

from __future__ import annotations

import errno
import socket
from collections.abc import Iterator
from types import ModuleType


class _Halt(BaseException):
    pass


class _Slow(TimeoutError):
    """메서드를 재정의하지 않은 TimeoutError 하위 클래스."""


_ROWS = {0: [5, 7, 11], 1: [100], 2: [], 3: [1, 1, 1, 1], 4: [True, 2, -3], 5: [10**30, 1]}


class _Source:
    """쪽마다 시도 계획대로 행을 내준다. 계획: ("ok",) · ("cut", k, 예외) · ("call", 예외) · ("mid", k, 예외).

    ok · cut · mid 끝에 행 목록을 더 주면 그 시도는 _ROWS 대신 그 행을 내준다 - 시도 사이에 원본이 바뀐 읽기.
    """

    def __init__(self, plans: dict[int, list[tuple[object, ...]]]) -> None:
        self.plans = plans
        self.calls: dict[int, int] = {}

    def __call__(self, page: int) -> Iterator[int]:
        n = self.calls.get(page, 0)
        self.calls[page] = n + 1
        spec = self.plans.get(page, [("ok",)])[min(n, len(self.plans.get(page, [("ok",)])) - 1)]
        if spec[0] == "call":
            raise spec[1]  # type: ignore[misc]
        return self._rows(page, spec)

    def _rows(self, page: int, spec: tuple[object, ...]) -> Iterator[int]:
        rows = _rows_of(page, spec)
        if spec[0] == "ok":
            yield from rows
            return
        yield from rows[: spec[1]]  # type: ignore[misc]
        raise spec[2]  # type: ignore[misc]


def _rows_of(page: int, spec: tuple[object, ...]) -> list[int]:
    """그 시도가 내주는 행 - 계획 끝에 붙은 목록이 있으면 그것."""
    extra = spec[1:] if spec[0] == "ok" else spec[3:]
    return list(extra[0]) if extra else _ROWS[page]  # type: ignore[call-overload]


def _expect(plans: dict[int, list[tuple[object, ...]]], pages: int) -> tuple[int | BaseException, dict[int, int]]:
    """주장 문장대로 - 쪽마다 3번까지 · 끝까지 받은 첫 시도의 행만 · 3번 다 끊기면 마지막 것 · 다른 예외는 바로."""
    amount, calls = 0, {}
    for page in range(pages):
        plan = plans.get(page, [("ok",)])
        for attempt in range(3):
            calls[page] = attempt + 1
            spec = plan[min(attempt, len(plan) - 1)]
            if spec[0] == "ok":
                amount += sum(_rows_of(page, spec))
                break
            error = spec[1] if spec[0] == "call" else spec[2]
            if not isinstance(error, TimeoutError) or attempt == 2:
                return error, calls  # type: ignore[return-value]
    return amount, calls


def _chained() -> ValueError:
    """원인 사슬에 TimeoutError 가 있는 ValueError - 시간 초과가 아니다."""
    err = ValueError("wrapped")
    err.__cause__ = TimeoutError("inner")
    return err


def _scenarios() -> list[tuple[dict[int, list[tuple[object, ...]]], int]]:
    t = TimeoutError
    return [
        ({}, 5),
        ({}, 0),
        ({}, -2),
        ({0: [("cut", 2, t()), ("ok",)]}, 5),  # 도중에 끊긴 뒤 성공 - 앞의 두 행을 다시 세면 안 된다
        ({0: [("cut", 1, t()), ("cut", 2, _Slow()), ("ok",)], 3: [("cut", 3, socket.timeout()), ("ok",)]}, 5),
        ({1: [("call", t()), ("ok",)]}, 3),  # 부르자마자 끊김
        ({0: [("cut", 2, t()), ("cut", 1, t()), ("cut", 3, t())]}, 2),  # 세 번 다 - 마지막 것을 올린다
        ({2: [("call", t()), ("call", t()), ("call", _Slow())]}, 4),
        ({0: [("cut", 1, ConnectionError())]}, 3),  # 시간 초과가 아닌 OSError - 다시 부르지 않는다
        ({4: [("mid", 1, ValueError("bad row"))]}, 5),
        ({1: [("call", KeyboardInterrupt())]}, 3),
        ({3: [("cut", 2, _Halt())]}, 5),
        ({}, 6),  # 2**53 을 넘는 금액 - float 로 더하면 틀린다
        ({2: [("call", OSError(errno.ETIMEDOUT, "timed out")), ("ok",)]}, 3),  # 생성자가 TimeoutError 를 돌려준다 - 다시 부른다
        ({0: [("cut", 1, t()), ("cut", 1, ConnectionResetError()), ("ok",)]}, 2),  # 재시도 중의 다른 예외
        ({1: [("call", ConnectionResetError()), ("call", ConnectionResetError()), ("ok",)]}, 3),  # 시도마다 다른 객체
        ({1: [("call", OSError(errno.EAGAIN, "again")), ("call", OSError(errno.EINTR, "intr")), ("ok",)]}, 3),
        ({2: [("mid", 0, RuntimeError("read timed out")), ("ok",)]}, 3),  # 메시지만 시간 초과
        ({0: [("call", _chained()), ("call", _chained()), ("ok",)]}, 2),  # 원인 사슬만 시간 초과
        ({1: [("call", StopIteration()), ("ok",)]}, 3),  # 부를 때의 StopIteration - 그대로 올린다
        # 끊긴 뒤 원본이 바뀐다 - 받은 행을 남기고 이어 받는 판은 끊긴 시도의 행을 합에 남긴다
        ({0: [("cut", 2, t(), [5, 7, 9]), ("ok", [6, 8, 11])]}, 1),
        ({0: [("cut", 3, t(), [1, 2, 3, 4]), ("cut", 1, t(), [40, 50]), ("ok", [10])]}, 2),
    ]


def attack(mod: ModuleType) -> bool:
    """합이나 부른 횟수가 주장과 다르거나, 올라와야 할 예외가 아닌 것이 올라오거나 아무것도 올라오지 않는가.

    🔴 끊김을 부르는 순간과 행을 내주는 도중 둘 다 친다 - 도중에 끊긴 시도의 앞부분 행이 남는 판은 도중 끊김에서만 보인다.
    🔴 올라온 예외는 받은 객체 그대로인지(is) 본다 - 세 번 다 끊기면 마지막 시도의 것이다.
    🔴 TimeoutError 의 하위 클래스(_Slow · errno 가 ETIMEDOUT 인 OSError 를 만들면 나오는 TimeoutError)는 다시 부른다.
       socket.timeout 은 3.10 부터 TimeoutError 의 별칭이라 하위 클래스 탐침이 아니다.
    🔴 시간 초과가 아닌 예외는 다시 부르지 않는다 - 다른 OSError(errno EAGAIN · EINTR 포함) · 메시지나 원인 사슬만 시간 초과인
       예외 · 재시도 중에 온 다른 예외 · 부를 때의 StopIteration(생성기 식 안에서 부르면 RuntimeError 로 바뀐다) · BaseException.
    🔴 금액은 2**53 을 넘는 정수도 정확히 더한다. 부른 횟수 비교는 주장의 「차례로」와 「다시 부르는 것은 ~뿐」을 본다.
    🔴 끊긴 뒤 원본이 바뀌는 읽기도 준다 - 받은 행을 남기고 다음 시도에서 그만큼 건너뛰는 판은 시도마다 행이 같으면
       합이 같아 보이지 않는다 (6라운드 검토).

    decoy 는 시도마다 쪽의 행을 끝까지 모은 뒤에야 더한다.
    twin 은 행을 받는 대로 더해, 도중에 끊긴 시도의 앞부분 행을 다시 받은 쪽에서 또 더한다.
    """
    for plans, pages in _scenarios():
        source = _Source(plans)
        want, want_calls = _expect(plans, pages)
        try:
            got: int | BaseException = mod.total(source, pages)
        except BaseException as caught:  # noqa: BLE001 - 무엇이 올라왔는지 본다
            got = caught
        if isinstance(want, BaseException):
            if got is not want:
                return True
        elif got != want:
            return True
        if source.calls != want_calls:
            return True
    return False
