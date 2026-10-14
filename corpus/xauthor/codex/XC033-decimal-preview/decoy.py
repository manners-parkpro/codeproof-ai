"""금액 반올림 미리보기 - 계산 컨텍스트를 복제해 설정과 누적 신호를 분리한다."""

from decimal import Context, Decimal, Inexact


def preview_amount(
    amount: Decimal, quantum: Decimal, template: Context, precision: int
) -> tuple[Decimal, Context]:
    working = template.copy()
    working.prec = precision
    working.clear_flags()
    working.traps[Inexact] = False
    result = working.quantize(amount, quantum)
    return result, working
