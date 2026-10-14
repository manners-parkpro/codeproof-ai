from enum import Enum, IntEnum, IntFlag
from types import ModuleType


class PlainInt(int):
    pass


class NamedInt(IntEnum):
    NEGATIVE = -3
    ZERO = 0
    POSITIVE = 5


class NamedFlags(IntFlag):
    LOW = 1
    HIGH = 8


class SignedFlags(IntFlag):
    ALL = -1
    ZERO = 0
    LOW = 1
    HIGH = 8


class MixedInt(int, Enum):
    NEGATIVE = -3
    ZERO = 0
    POSITIVE = 5


class RetryTimeout(TimeoutError):
    pass


class CallbackAbort(BaseException):
    pass


AXES = (
    ("initial", "zero, positive, negative, large, ordinary subtypes"),
    ("mask", "zero, overlap, disjoint, negative, large, ordinary subtypes"),
    ("attempts", "negative, zero, one, retries, huge, ordinary subtypes"),
    ("history", "success, timeout, exhaustion, propagated exception, repeated masks"),
    ("observation", "inside callback and after normal or exceptional completion"),
    ("unclaimed", "return value, exception type, representation"),
)


def _removed(before: int, mask: int) -> int:
    width = max(int(before).bit_length(), int(mask).bit_length()) + 2
    result = sum(
        2 ** bit
        for bit in range(width)
        if (before >> bit) % 2 and not (mask >> bit) % 2
    )
    if result >= 2 ** (width - 1):
        result -= 2 ** width
    return result


def _probe(flags, mask, attempts, outcomes) -> bool:
    before = flags.snapshot()
    expected = _removed(before, mask) if attempts > 0 else before
    observed = []
    calls = 0

    def acknowledge():
        nonlocal calls
        observed.append(flags.snapshot())
        outcome = outcomes[min(calls, len(outcomes) - 1)]
        calls += 1
        if outcome is not None:
            raise outcome

    try:
        flags.disable(mask, acknowledge, attempts)
    except BaseException:
        pass
    return flags.snapshot() != expected or any(
        value != expected for value in observed
    )


def attack(mod: ModuleType) -> bool:
    timeout = TimeoutError("lost confirmation")
    retry_timeout = RetryTimeout("late confirmation")
    fatal = ValueError("confirmation refused")
    abort = CallbackAbort("synchronous callback abort")
    retry_case = mod.FeatureFlags(3)
    if _probe(retry_case, 1, 2, (timeout, None)):
        return True
    schedules = (
        (-3, (None,)),
        (0, (None,)),
        (1, (None,)),
        (1, (timeout,)),
        (2, (timeout, None)),
        (2, (timeout,)),
        (5, (timeout, timeout, timeout, timeout, None)),
        (6, (retry_timeout,)),
        (4, (fatal,)),
        (4, (timeout, fatal)),
        (3, (abort,)),
        (3, (timeout, abort)),
        (False, (None,)),
        (True, (None,)),
        (PlainInt(0), (None,)),
        (PlainInt(3), (timeout, None)),
        (NamedInt.NEGATIVE, (None,)),
        (NamedInt.ZERO, (None,)),
        (NamedInt.POSITIVE, (timeout, None)),
        (SignedFlags.ALL, (None,)),
        (SignedFlags.LOW, (None,)),
        (NamedFlags.LOW, (None,)),
        (NamedFlags.HIGH, (timeout, None)),
        (MixedInt.ZERO, (None,)),
        (MixedInt.POSITIVE, (timeout, None)),
        (2 ** 256, (None,)),
        (2 ** 256, (fatal,)),
        (-2 ** 256, (None,)),
    )
    values = tuple(range(-4, 5)) + (
        False, True, PlainInt(-7), PlainInt(0), PlainInt(9),
        NamedInt.NEGATIVE, NamedInt.ZERO, NamedInt.POSITIVE,
        NamedFlags(0), NamedFlags.LOW, NamedFlags.HIGH, NamedFlags(9),
        SignedFlags.ALL, SignedFlags.ZERO, SignedFlags.LOW, SignedFlags.HIGH,
        MixedInt.NEGATIVE, MixedInt.ZERO, MixedInt.POSITIVE,
    )
    pairs = [(initial, mask) for initial in values for mask in values]
    boundaries = (
        2 ** 31, 2 ** 63, 2 ** 64, 2 ** 128, 2 ** 4096,
    )
    for boundary in boundaries:
        for delta in (-1, 0, 1):
            value = boundary + delta
            pairs.extend((
                (value, 1), (value, boundary), (value, -1),
                (-value, boundary), (-value, -boundary),
                (1, value), (-1, value), (0, -value),
                (value, 2 ** (boundary.bit_length() + 1)),
            ))

    default = mod.FeatureFlags()
    if default.snapshot() != 0:
        return True
    for initial, mask in pairs:
        for attempts, outcomes in schedules:
            flags = mod.FeatureFlags(initial)
            if flags.snapshot() != initial:
                return True
            if _probe(flags, mask, attempts, outcomes):
                return True

    for initial in (0, -1, 0b101101, -(2 ** 128), PlainInt(37)):
        flags = mod.FeatureFlags(initial)
        for mask, attempts, outcomes in (
            (0b001001, 1, (None,)),
            (0b001001, 2, (timeout, None)),
            (0b000110, 2, (timeout,)),
            (0b010000, 3, (fatal,)),
            (0b100000, 3, (timeout, abort)),
            (0, 4, (timeout, None)),
            (-8, 3, (timeout, None)),
            (2 ** 140, 0, (None,)),
            (-1, -1, (None,)),
            (-1, 3, (timeout, None)),
            (-1, 1, (None,)),
        ):
            if _probe(flags, mask, attempts, outcomes):
                return True
    return False
