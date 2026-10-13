from decimal import (
    Context, Decimal, Inexact, InvalidOperation, Rounded, Subnormal,
    MAX_PREC, MAX_EMAX, MIN_EMIN,
    ROUND_05UP, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR,
    ROUND_HALF_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP,
)
from enum import IntEnum
from types import ModuleType


class PlainContext(Context):
    pass


class PlainDecimal(Decimal):
    pass


class PlainInt(int):
    pass


class Digits(IntEnum):
    SMALL = 3


ATTRS = ("prec", "rounding", "Emin", "Emax", "capitals", "clamp")
SIGNALS = tuple(Context().flags)
ROUNDINGS = (
    ROUND_05UP, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR,
    ROUND_HALF_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP,
)


def state(context):
    return (
        tuple(getattr(context, name) for name in ATTRS),
        tuple(bool(context.flags[signal]) for signal in SIGNALS),
        tuple(bool(context.traps[signal]) for signal in SIGNALS),
    )


def independent(left, right):
    for changed, observed in ((left, right), (right, left)):
        baseline = state(observed)
        for name, value in (
            ("prec", 17 if changed.prec != 17 else 18),
            ("rounding", ROUND_UP if changed.rounding != ROUND_UP else ROUND_DOWN),
            ("Emin", -13 if changed.Emin != -13 else -7),
            ("Emax", 13 if changed.Emax != 13 else 7),
            ("capitals", 1 - changed.capitals),
            ("clamp", 1 - changed.clamp),
        ):
            setattr(changed, name, value)
            if state(observed) != baseline:
                return False
        for name in ("flags", "traps"):
            mapping = getattr(changed, name)
            for signal in SIGNALS:
                mapping[signal] = not mapping[signal]
                if state(observed) != baseline:
                    return False
            setattr(changed, name, {signal: True for signal in SIGNALS})
            if state(observed) != baseline:
                return False
            getattr(changed, "clear_" + name)()
            if state(observed) != baseline:
                return False
    return True


def violates(mod, template, amount, quantum, precision):
    before = state(template)
    rejected = False
    try:
        expected = Context(
            prec=precision,
            rounding=template.rounding,
            Emin=template.Emin,
            Emax=template.Emax,
            capitals=template.capitals,
            clamp=template.clamp,
            flags=[],
            traps=[s for s in SIGNALS if s is not Inexact and template.traps[s]],
        )
        value = amount.quantize(quantum, context=expected)
        after = state(expected)
    except Exception:
        rejected = True
    try:
        result, working = mod.preview_amount(amount, quantum, template, precision)
    except Exception:
        return state(template) != before or not rejected
    if state(template) != before or rejected:
        return True
    if not isinstance(result, Decimal) or not isinstance(working, Context):
        return True
    if result.as_tuple() != value.as_tuple() or state(working) != after:
        return True
    return not independent(template, working)


def cases():
    for mask in range(1 << len(SIGNALS)):
        flags = [s for i, s in enumerate(SIGNALS) if mask & (1 << i)]
        yield Context(prec=9, flags=flags, traps=[]), Decimal("1.25"), Decimal(".1"), 9
        yield Context(prec=9, flags=flags, traps=[]), Decimal("1.00"), Decimal(".01"), 9
        yield Context(prec=9, flags=flags, traps=[InvalidOperation]), Decimal("sNaN"), Decimal("1"), 5
    for mask in range(1 << len(SIGNALS)):
        traps = [s for i, s in enumerate(SIGNALS) if mask & (1 << i)]
        for number in ("1.25", "sNaN", "Infinity", "1E+10", "1E-10"):
            yield Context(prec=9, Emin=-3, Emax=3, traps=traps), Decimal(number), Decimal(".1"), 5
    for rounding in ROUNDINGS:
        for clamp in (0, 1):
            for capitals in (0, 1):
                for number in ("1.25", "-1.25", "0.05", "-0.05", "-0", "9.999", "1E+5", "0.00001"):
                    for quantum in (".1", ".01", "1E+2", "1E-6"):
                        yield Context(
                            prec=8, rounding=rounding, Emin=-3, Emax=3,
                            capitals=capitals, clamp=clamp, traps=[],
                        ), Decimal(number), Decimal(quantum), 3
    for number in ("0", "-0", "NaN", "-NaN12", "sNaN42", "Infinity", "-Infinity", "1E+999999", "1E-999999"):
        for quantum in ("0.01", "0", "-0", "NaN2", "sNaN3", "Infinity", "1E+999999", "1E-999999"):
            yield Context(traps=[]), Decimal(number), Decimal(quantum), 28
    for precision in (-10**100, -1, 0, False, True, PlainInt(3), Digits.SMALL, 1, 28, 1000, MAX_PREC, MAX_PREC + 1, 10**100):
        for flags in ([], list(SIGNALS)):
            yield Context(flags=flags, traps=[Inexact, Rounded]), Decimal("1.25"), Decimal(".1"), precision
            yield Context(flags=flags, traps=[]), Decimal("1"), Decimal("1"), precision
    for cls in (Context, PlainContext):
        for decimal_cls in (Decimal, PlainDecimal):
            yield cls(
                prec=19, rounding=ROUND_FLOOR, Emin=MIN_EMIN,
                Emax=MAX_EMAX, flags=[Subnormal], traps=[Inexact],
            ), decimal_cls("-1.25"), decimal_cls(".1"), PlainInt(6)
    for boundary in (0, 1, 10, MAX_EMAX):
        yield Context(Emin=-boundary, Emax=boundary, traps=[]), Decimal("1"), Decimal("1"), 2


def attack(mod: ModuleType) -> bool:
    for template, amount, quantum, precision in cases():
        if violates(mod, template, amount, quantum, precision):
            return True
    return False
