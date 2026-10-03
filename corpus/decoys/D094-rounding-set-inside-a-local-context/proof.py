"""D094 반증 - total 을 부른 뒤 스레드의 decimal 문맥이 바뀌었는지 본다."""

from __future__ import annotations

import decimal
from types import ModuleType


def _state() -> tuple[object, ...]:
    ctx = decimal.getcontext()
    return (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin, ctx.capitals, ctx.clamp, dict(ctx.traps), dict(ctx.flags))


def attack(mod: ModuleType) -> bool:
    """정상 경로나 예외 경로에서 호출 스레드의 decimal 문맥이 바뀌는가.

    🔴 시작 문맥을 기본값이 아닌 값(정밀도 10 · ROUND_DOWN · Inexact 플래그)으로 세운다 - 기본값에서
       시작하면 「저장한 문맥 대신 기본값으로 되돌리는」 약화와 정밀도 28 누수가 보이지 않는다 (독립 검토).
       끝나면 원래 문맥으로 되돌린다 - twin 이 바꾼 문맥이 같은 프로세스의 다른 증명 · 테스트로 새면 안 된다.
    🔴 예외는 total 안에서 동기로 던진다 - 시그널 처리기의 비동기 예외는 주장 밖이다 (meta.toml).
    예외는 ValueError · KeyboardInterrupt · 사용자 정의 BaseException 을 친다 (DESIGN §3.5 「예외」).

    decoy 는 localcontext 의 사본에만 써서 블록을 나가면 원래 문맥이 돌아온다.
    twin 은 현재 문맥에 직접 써서 정밀도와 반올림이 남는다.
    """
    saved = decimal.getcontext().copy()
    decimal.setcontext(decimal.Context(prec=10, rounding=decimal.ROUND_DOWN, flags=[decimal.Inexact]))
    try:
        before = _state()
        # HALF_UP 이면 0.125 -> 0.13 (기본 HALF_EVEN 이면 0.12)
        if mod.total(["0.125"]) != decimal.Decimal("0.13") or _state() != before:
            return True
        for error in (ValueError("가격 읽기 실패"), KeyboardInterrupt(), _Abort()):
            try:
                mod.total(_Prices(error))
            except BaseException as caught:  # noqa: BLE001 - 던진 것이 그대로 올라왔는지만 본다
                if caught is not error:
                    return True
            if _state() != before:
                return True
        # 숫자로 읽을 수 없는 가격(decimal 이 InvalidOperation 을 낸다)도 문맥을 남기지 않는다
        try:
            mod.total(["1.00", "열두 원"])
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다, 문맥만 본다
            pass
        return _state() != before
    finally:
        decimal.setcontext(saved)


class _Abort(BaseException):
    """Exception 도 KeyboardInterrupt 도 아닌 중단."""


class _Prices(list[str]):
    """두 번째 가격을 꺼낼 때 주어진 예외를 던진다 - 계산 도중에 끝나는 경로를 만든다."""

    def __init__(self, error: BaseException) -> None:
        super().__init__(["1.005", "2.005"])
        self._error = error

    def __iter__(self):  # type: ignore[override]
        yield "1.005"
        raise self._error
