from enum import IntEnum
from itertools import product
from types import ModuleType


class Payload(bytes):
    pass


class Attempts(int):
    pass


class RetryCount(IntEnum):
    NEGATIVE = -2
    ZERO = 0
    ONCE = 1
    SEVERAL = 4


class SlowAck(TimeoutError):
    pass


class AckAbort(BaseException):
    pass


class Reply:
    def __init__(self, errors: tuple[type[BaseException], ...]) -> None:
        self.errors = errors
        self.index = 0

    def __call__(self) -> None:
        index = self.index
        self.index += 1
        if index < len(self.errors):
            raise self.errors[index]()


SEEDS = (
    b"",
    b"prefix",
    b"\x00\xff\x80",
    bytes(range(256)),
    b"x" * 4097,
    Payload(b"subclass seed"),
)
PAYLOADS = (
    b"",
    b"a",
    b"prefix",
    b"\x00\xff\x00",
    bytes(range(256)),
    b"large" * 1001,
    Payload(b"subclass payload"),
    Payload(b""),
)
COUNTS = (
    -(10**100),
    -1,
    0,
    1,
    2,
    7,
    False,
    True,
    Attempts(-3),
    Attempts(0),
    Attempts(3),
    RetryCount.NEGATIVE,
    RetryCount.ZERO,
    RetryCount.ONCE,
    RetryCount.SEVERAL,
)
REPLIES = (
    (),
    (TimeoutError,),
    (TimeoutError, TimeoutError),
    (TimeoutError,) * 7,
    (SlowAck,) * 7,
    (ValueError,),
    (OSError,),
    (AckAbort,),
    (SystemExit,),
    (TimeoutError, ValueError),
    (TimeoutError, AckAbort),
)


def _step(spool, before: bytes, payload: bytes, attempts: int, errors) -> bool:
    expected = before + payload if attempts > 0 else before
    try:
        spool.append(payload, Reply(errors), attempts)
    except BaseException:
        pass
    return spool.snapshot() != expected


def attack(mod: ModuleType) -> bool:
    for initial, payload, attempts, errors in product(
        SEEDS, PAYLOADS, COUNTS, REPLIES
    ):
        spool = mod.UploadSpool(initial)
        if spool.snapshot() != initial:
            return True
        if _step(spool, initial, payload, attempts, errors):
            return True

    for initial in SEEDS:
        spool = mod.UploadSpool(initial)
        expected = bytes(initial)
        saved = []
        steps = (
            (b"first", 4, (TimeoutError, TimeoutError)),
            (b"first", 2, (TimeoutError,)),
            (b"", 3, (TimeoutError,) * 3),
            (Payload(b"next\x00"), RetryCount.SEVERAL, (ValueError,)),
            (b"unused", 0, ()),
            (b"also unused", -(10**100), ()),
            (bytes(range(256)), Attempts(3), (SlowAck,) * 3),
            (b"after error", 2, (TimeoutError, AckAbort)),
            (b"x" * 5001, 3, (TimeoutError,) * 3),
            (b"end", True, ()),
        )
        for payload, attempts, errors in steps:
            saved.append((spool.snapshot(), expected))
            if _step(spool, expected, payload, attempts, errors):
                return True
            if attempts > 0:
                expected += payload
            if any(snapshot != value for snapshot, value in saved):
                return True

    for attempts in (10**100, Attempts(10**100)):
        spool = mod.UploadSpool(b"huge count")
        if _step(spool, b"huge count", b"data", attempts, (TimeoutError,)):
            return True

    spool = mod.UploadSpool()
    try:
        spool.append(b"default", Reply((TimeoutError, TimeoutError)))
    except BaseException:
        pass
    return spool.snapshot() != b"default"
