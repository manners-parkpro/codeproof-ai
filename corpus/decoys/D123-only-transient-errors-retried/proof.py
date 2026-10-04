"""D123 반증 - 예외 종류 · attempts · 실패 순서마다 job 을 부른 횟수와 run 이 던진 객체를 센다."""

from __future__ import annotations

import errno
from collections.abc import Callable
from types import ModuleType


class _Custom(Exception):
    pass


class _Stop(BaseException):
    pass


class _SlowNetwork(TimeoutError):
    pass


class _CustomButConnection(_Custom, ConnectionError):
    """ConnectionError 이기도 하다 - 재시도 대상이다."""


# 🔴 다시 던져야 하는 것 - OSError 이지만 일시 오류가 아닌 것 · Exception 이 아닌 BaseException 까지
_FATAL: list[type[BaseException]] = [
    ValueError, TypeError, KeyError, RuntimeError, StopIteration, OSError, FileNotFoundError, PermissionError,
    _Custom, _Stop, KeyboardInterrupt, SystemExit,
]
# 삼켜도 되는 것 - 하위 클래스와 다중 상속까지
_TRANSIENT: list[type[BaseException]] = [
    TimeoutError, ConnectionError, ConnectionResetError, ConnectionRefusedError, BrokenPipeError,
    _SlowNetwork, _CustomButConnection,
]


class _Valued:
    """값을 가진 예외를 만드는 plan 한 칸 - 메시지 · errno · 원인 사슬로 분류하는 약화를 가른다 (독립 검토)."""

    def __init__(self, make: Callable[[], BaseException]) -> None:
        self.make = make


def _caused_by_connection() -> BaseException:
    error = ValueError("응답이 깨졌다")
    error.__cause__ = ConnectionError("끊김")
    return error


def _while_timing_out() -> BaseException:
    error = ValueError("응답이 깨졌다")
    error.__context__ = TimeoutError("시간 초과")
    return error


# 다시 던져야 하는 것 - 메시지에 timeout 이 있거나 · errno 가 EAGAIN · EINTR 이거나 · 원인이 일시 오류라도 타입이 일시 오류가 아니다
_VALUED_FATAL: list[Callable[[], BaseException]] = [
    lambda: ValueError("upstream timeout"), lambda: RuntimeError("connection reset by peer"),
    lambda: OSError(errno.EAGAIN, "busy"), lambda: OSError(errno.EINTR, "interrupted"), _caused_by_connection, _while_timing_out,
]
# 삼켜도 되는 것 - errno 로 만들어진 일시 오류 하위 클래스 · 메시지가 있는 TimeoutError
_VALUED_TRANSIENT: list[Callable[[], BaseException]] = [
    lambda: OSError(errno.ETIMEDOUT, "timed out"), lambda: OSError(errno.ECONNRESET, "reset"), lambda: TimeoutError("read timeout"),
]
_ATTEMPTS = [1, True, 2, 3, 5, 6, 13]
_SUCCESS: list[object] = ["값", None, 0, False, "", object()]  # 🔴 None · 거짓 값도 성공이다 (쓰는 단계 점검)
_REJECTED = [0, False, -1, -5]


def _job(plan: list[object], calls: list[object], made: list[BaseException]) -> Callable[[], object]:
    """plan 을 차례대로 - 예외 클래스면 새 객체를 만들어 던지고 그 밖의 값은 돌려준다. 끝에 닿으면 마지막 것을 되풀이한다."""

    def job() -> object:
        step = plan[min(len(calls), len(plan) - 1)]
        calls.append(step)
        if isinstance(step, type) and issubclass(step, BaseException):
            made.append(step())
            raise made[-1]
        if isinstance(step, _Valued):
            made.append(step.make())
            raise made[-1]
        return step

    return job


def _run(mod: ModuleType, plan: list[object], attempts: int) -> tuple[object, BaseException | None, int, list[BaseException]]:
    """(돌려준 값, 던진 객체, job 을 부른 횟수, job 이 만든 예외들)."""
    calls: list[object] = []
    made: list[BaseException] = []
    try:
        value = mod.run(_job(plan, calls, made), attempts)
    except BaseException as caught:  # noqa: BLE001 - KeyboardInterrupt · SystemExit 까지 job 이 던진 것이다
        return None, caught, len(calls), made
    return value, None, len(calls), made


def attack(mod: ModuleType) -> bool:
    """run 이 다시 던져야 할 예외를 삼키거나, 재시도 횟수가 attempts 와 다르거나, 던진 객체가 job 의 것이 아니면 True.

    🔴 「그 예외 객체를 그대로」는 동일성(is)으로 본다 - 새 예외로 감싸 던지면 타입이 같아도 깨진다.
    🔴 일시 오류는 하위 클래스 · 다중 상속까지, 치명 오류는 OSError 형제와 BaseException 까지 친다 -
       OSError 전체를 재시도하거나 ConnectionError 만 재시도하는 약화가 지나가지 않게.
    🔴 거절은 「job 을 한 번도 부르지 않았는가」만 본다 - 어떤 예외로 거절하든 묻지 않는다.

    decoy 는 _classify 가 _RETRYABLE 이 아닌 예외를 받은 객체 그대로 다시 던진다.
    twin 은 except 가 모든 Exception 을 삼키고 마지막 호출까지 job 을 다시 부른다.
    """
    for attempts in _REJECTED:
        _, caught, calls, _ = _run(mod, ["값"], attempts)
        if caught is None or calls != 0:
            return True
    for attempts in _ATTEMPTS:
        n = int(attempts)
        for fatal in _FATAL:
            for before in range(n):  # 일시 오류 before 번 뒤에 치명 오류
                _, caught, calls, made = _run(mod, [TimeoutError] * before + [fatal], attempts)
                if calls != before + 1 or caught is not made[-1]:
                    return True
        for transient in _TRANSIENT:
            _, caught, calls, made = _run(mod, [transient], attempts)
            if calls != n or caught is not made[-1]:
                return True
            for before in range(n):  # 일시 오류 before 번 뒤에 성공 - 어떤 값이든 그 객체 그대로
                for success in _SUCCESS:
                    value, caught, calls, _ = _run(mod, [transient] * before + [success], attempts)
                    if caught is not None or value is not success or calls != before + 1:
                        return True
    # 🔴 값을 가진 예외 - 타입이 아니라 메시지 · errno · 원인 사슬로 재시도를 고르는 약화가 지나가지 않게 (독립 검토)
    for attempts in (2, 3):
        for make in _VALUED_FATAL:
            for before in range(attempts):
                _, caught, calls, made = _run(mod, [TimeoutError] * before + [_Valued(make)], attempts)
                if calls != before + 1 or caught is not made[-1]:
                    return True
        for make in _VALUED_TRANSIENT:
            _, caught, calls, made = _run(mod, [_Valued(make)], attempts)
            if calls != attempts or caught is not made[-1]:
                return True
    # 🔴 attempts 가 커도 같다 - 상한을 둔 판 · 재귀 판(RecursionError)이 빠지지 않게 (쓰는 단계 점검)
    _, caught, calls, made = _run(mod, [TimeoutError], 2000)
    return calls != 2000 or caught is not made[-1]
