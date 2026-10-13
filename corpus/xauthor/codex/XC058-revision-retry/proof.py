from enum import IntEnum, IntFlag
from types import ModuleType


class PlainInt(int):
    pass


class Number(IntEnum):
    NEGATIVE = -9
    ZERO = 0
    POSITIVE = 3


class Bits(IntFlag):
    ZERO = 0
    ONE = 1
    FOUR = 4


class DeliveryStopped(BaseException):
    pass


class SlowAck(TimeoutError):
    pass


AXES = {
    "construction": ("zero", "signed", "large", "subtypes"),
    "delta": ("zero", "signed", "large", "subtypes"),
    "attempts": ("negative", "zero", "one", "many", "large", "subtypes"),
    "acknowledgement": ("success", "lost", "recovered", "exception", "base_exception"),
    "history": ("fresh", "same_delta", "zero_delta", "cancel", "failed_ack", "no_attempt"),
    "observation": ("inside_callback", "after_return", "after_exception"),
    "safe_variants": ("container", "exception_type", "branch_shape", "normalization"),
}


VALUES = (
    0, 1, -1, 17, -23, 2**63, -(2**63), 2**2048, -(2**2048),
    False, True, PlainInt(-8), PlainInt(6),
    Number.NEGATIVE, Number.ZERO, Number.POSITIVE,
    Bits.ZERO, Bits.ONE, Bits.ONE | Bits.FOUR,
)
ATTEMPT_VALUES = (
    -4, 0, 1, 2, 4, -(2**2048), False, True,
    PlainInt(-2), PlainInt(3), Number.NEGATIVE, Number.ZERO,
    Number.POSITIVE, Bits.ZERO, Bits.ONE, Bits.ONE | Bits.FOUR,
)
ACKS = (
    ("ok",),
    ("timeout",),
    ("slow", "ok"),
    ("timeout", "timeout", "ok"),
    ("error",),
    ("timeout", "error"),
    ("stop",),
    ("timeout", "stop"),
)


def exercise(account, before, delta, attempts, outcomes):
    expected = (
        (before[0] + int(delta), before[1] + 1)
        if int(attempts) > 0 else before
    )
    observed = []
    calls = 0

    def acknowledge():
        nonlocal calls
        observed.append(tuple(account.snapshot()))
        outcome = outcomes[min(calls, len(outcomes) - 1)]
        calls += 1
        if calls > 8:
            raise DeliveryStopped()
        if outcome == "timeout":
            raise TimeoutError("lost")
        if outcome == "slow":
            raise SlowAck("late")
        if outcome == "error":
            raise ValueError("rejected acknowledgement")
        if outcome == "stop":
            raise DeliveryStopped()

    try:
        account.adjust(delta, acknowledge, attempts)
    except BaseException:
        pass
    broken = (
        tuple(account.snapshot()) != expected
        or any(value != expected for value in observed)
    )
    return broken, expected


def attack(mod: ModuleType) -> bool:
    for initial in VALUES:
        for delta in VALUES:
            for attempts in ATTEMPT_VALUES:
                for outcomes in ACKS:
                    account = mod.Balance(initial)
                    before = (int(initial), 0)
                    if tuple(account.snapshot()) != before:
                        return True
                    broken, _ = exercise(account, before, delta, attempts, outcomes)
                    if broken:
                        return True

    left = mod.Balance(31)
    right = mod.Balance(-19)
    left_state, right_state = (31, 0), (-19, 0)
    for _ in range(260):
        broken, left_state = exercise(left, left_state, 2, 3, ("timeout", "ok"))
        if broken or tuple(right.snapshot()) != right_state:
            return True
        broken, right_state = exercise(right, right_state, -3, 2, ("timeout",))
        if broken or tuple(left.snapshot()) != left_state:
            return True

    history = (
        (7, 3, ("timeout",)),
        (7, 2, ("timeout", "ok")),
        (0, 4, ("timeout",)),
        (-14, 3, ("timeout", "error")),
        (2**2048, 0, ("ok",)),
        (Number.NEGATIVE, Number.POSITIVE, ("slow", "ok")),
        (PlainInt(12), -3, ("ok",)),
        (Bits.ONE | Bits.FOUR, 1, ("stop",)),
        (True, True, ("ok",)),
        (-(2**2048), 4, ("timeout", "stop")),
        (2**2048, 2**2048, ("timeout", "timeout", "ok")),
        (0, PlainInt(2**2048), ("ok",)),
    )
    for initial in VALUES:
        account = mod.Balance(initial)
        before = (int(initial), 0)
        for _ in range(3):
            for delta, attempts, outcomes in history:
                broken, before = exercise(account, before, delta, attempts, outcomes)
                if broken:
                    return True
    return False
