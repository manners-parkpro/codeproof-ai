"""D148 반증 - save 가 던지는 여러 예외(값을 가진 것 포함)가 그대로 올라오고 extras 가 불리지 않는지, save 가 끝나면 extras 의
자리마다 차례대로 한 번씩 부르고 예외 없이 끝난 단계를 세는지, 단계의 BaseException(섞인 그룹 포함)은 그대로 올라오는지 본다."""

from __future__ import annotations

import errno
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType


class _Custom(Exception):
    """표준 라이브러리 밖의 Exception 하위 클래스."""


class _Halt(BaseException):
    """Exception 이 아닌 사용자 BaseException 하위 클래스."""


_SAVE_ERRORS: tuple[type[BaseException], ...] = (
    ValueError, OSError, KeyError, StopIteration, RuntimeError, _Custom, KeyboardInterrupt, SystemExit, _Halt,
)
_STEP_ERRORS: tuple[type[Exception], ...] = (ValueError, OSError, LookupError, StopIteration, ZeroDivisionError, _Custom)
_STEP_HALTS: tuple[type[BaseException], ...] = (KeyboardInterrupt, SystemExit, GeneratorExit, _Halt)


def attack(mod: ModuleType) -> bool:  # noqa: C901, PLR0911
    """규칙을 하나라도 어기면 True.

    🔴 save 의 예외는 종류마다 친다 - 표준 · 사용자 정의 · Exception 이 아닌 것 · 예외 그룹(원소 하나 · 둘 · 섞인
       BaseExceptionGroup)까지. 「그대로」는 같은 객체이고 원인 사슬(__cause__ · __context__ · __suppress_context__)도 그대로다
       - 그룹을 풀거나 except* 로 나누거나 from None 으로 다시 올리는 판 (6라운드 검토).
    🔴 처음 한 번만 실패하는 save 도 친다 - 다시 부르면 첫 예외를 삼킨 것이다.
    🔴 단계의 실패는 Exception 의 여러 하위 클래스로 친다 - 일부만 삼키는 약화가 빠지지 않게.
    🔴 단계의 BaseException 은 그대로 올라와야 한다 - Exception 이 섞인 BaseExceptionGroup 도 같은 객체다 (suppress · except* 는
       그룹을 나눠 새 그룹을 올린다). BaseException 을 낸 단계가 둘이면 처음 것이 올라오고 둘째는 불리지 않는다 - 불리면 둘째를
       삼킨 것이다. 하나뿐이면 그 뒤 단계를 부르는지는 주장 밖이다.
    🔴 save 의 예외는 값을 가진 것(TimeoutError · errno EAGAIN · 원인 사슬)으로도 치고, extras 가 비거나 여럿일 때 모두 본다.
    🔴 extras 는 크기(1000자리)와 같은 단계 객체가 여러 자리에 있는 경우도 친다 - 자리마다 한 번씩이다.
    🔴 단계가 extras 를 비우거나 늘리고 save 가 늘린다 - 부를 자리는 publish 를 부른 때의 extras 다 (세 번째 렌즈).

    decoy 는 save 를 직접 불러 그 예외가 그대로 올라간다.
    twin 은 save 도 _quietly 로 불러 Exception 이 삼켜진다.
    """
    calls: list[object] = []

    def step(name: object, error: BaseException | None = None) -> Callable[[], None]:
        def run() -> None:
            calls.append(name)
            if error is not None:
                raise error

        return run

    def save_ok() -> None:
        calls.append("save")

    def chained() -> BaseException:
        exc = RuntimeError("저장 실패")
        exc.__cause__ = TimeoutError("timeout")
        return exc

    makers = [lambda kind=kind: kind("저장 실패") for kind in _SAVE_ERRORS]
    makers += [lambda: TimeoutError("save timeout"), lambda: OSError(errno.EAGAIN, "try again"), chained]
    # 예외 그룹 - 원소 하나 · 둘 · Exception 이 섞인 BaseExceptionGroup (풀거나 나눠 다른 객체를 올리는 판)
    makers += [
        lambda: ExceptionGroup("저장 실패", [OSError("disk full")]),
        lambda: ExceptionGroup("저장 실패", [ValueError("a"), KeyError("b")]),
        lambda: BaseExceptionGroup("저장 실패", [KeyboardInterrupt(), ValueError("c")]),
    ]
    for make, flaky, shape in [(m, f, n) for m in makers for f in (False, True) for n in (0, 1, 2, 20)]:
        boom = make()
        chain = (boom.__cause__, boom.__context__, boom.__suppress_context__)
        tries: list[int] = []

        def save(boom: BaseException = boom, tries: list[int] = tries, flaky: bool = flaky) -> None:
            calls.append("save")
            tries.append(1)
            if not flaky or len(tries) == 1:
                raise boom

        calls.clear()
        try:
            mod.publish(save, [step(f"x{i}") for i in range(shape)])
        except BaseException as caught:  # noqa: BLE001
            if caught is not boom or (caught.__cause__, caught.__context__, caught.__suppress_context__) != chain:
                return True
        else:
            return True
        if calls != ["save"]:
            return True

    patterns: list[list[BaseException | None]] = [[], [None], [None, None, None]]
    patterns += [[kind("단계 실패")] for kind in _STEP_ERRORS]
    patterns += [[None, kind("단계 실패"), None, _Custom("둘째"), None] for kind in _STEP_ERRORS]
    patterns += [[None] * 1000, [None if i % 3 else ValueError("단계 실패") for i in range(1000)]]
    for pattern in patterns:
        calls.clear()
        try:
            done = mod.publish(save_ok, [step(i, err) for i, err in enumerate(pattern)])
        except Exception:  # noqa: BLE001
            return True
        if calls != ["save", *range(len(pattern))] or done != sum(err is None for err in pattern):
            return True

    same_ok, same_bad = step("같음"), step("같은 실패", ValueError("실패"))
    calls.clear()
    done = mod.publish(save_ok, [same_ok, step(1), same_bad, same_ok, same_bad])
    if calls != ["save", "같음", 1, "같은 실패", "같음", "같은 실패"] or done != 3:
        return True

    b1, b2 = KeyboardInterrupt("첫"), SystemExit("둘")
    calls.clear()
    try:
        mod.publish(save_ok, [step(0), step(1, b1), step(2, b2), step(3)])
    except BaseException as caught:  # noqa: BLE001
        if caught is not b1 or 2 in calls:
            return True
    else:
        return True

    halts = [kind("멈춤") for kind in _STEP_HALTS]
    halts.append(BaseExceptionGroup("멈춤", [KeyboardInterrupt("멈춤"), ValueError("실패")]))
    for boom in halts:
        calls.clear()
        try:
            mod.publish(save_ok, [step(0), step(1, boom), step(2)])
        except BaseException as caught:  # noqa: BLE001
            if caught is not boom:
                return True
        else:
            return True
        if calls not in (["save", 0, 1], ["save", 0, 1, 2]):
            return True

    # 단계나 save 가 extras 를 바꾼다 - 부를 자리는 publish 를 부른 때의 것이다
    extras: list[Callable[[], None]] = []

    def clearing() -> None:
        calls.append("비움")
        extras.clear()

    def growing() -> None:
        calls.append("늘림")
        extras.append(step("늘어난 단계"))

    def save_grows() -> None:
        calls.append("save")
        extras.append(step("save 가 더한 단계"))

    for saver, start, want in (
        (save_ok, [clearing, step(1), step(2)], ["save", "비움", 1, 2]),
        (save_ok, [growing, step(1)], ["save", "늘림", 1]),
        (save_grows, [step(0)], ["save", 0]),
    ):
        extras[:] = start
        calls.clear()
        if mod.publish(saver, extras) != len(start) or calls != want:
            return True
    return False
