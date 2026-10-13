from enum import Enum, IntEnum, IntFlag
from itertools import product
from types import ModuleType


class Text(str):
    pass


class Count(int):
    pass


class TextEnum(str, Enum):
    RAW = "A&&amp;&AMP;\x00\ud800"
    EMPTY = ""
    READY = "&amp;"


class Counts(IntEnum):
    NEGATIVE = -3
    ZERO = 0
    ONE = 1
    MANY = 4


class Flags(IntFlag):
    ZERO = 0
    ONE = 1
    TWO = 2


def expected(text: str) -> str:
    return "".join(
        "&amp;" if char == "&" and text[i + 1:i + 5] != "amp;" else char
        for i, char in enumerate(text)
    )


def samples() -> list[str]:
    atoms = ("&", "amp;", "&amp;", "a", ";", "\n", "한")
    texts = ["".join(parts) for size in range(4) for parts in product(atoms, repeat=size)]
    texts += [
        "&a", "&am", "&amp", "&AMP;", "&Amp;", "&amP;", "&ampX",
        "&amp\n;", "&\namp;", "&#38;", "&#x26;", "&lt;", "&quot;",
        "&amp;amp;", "&&amp;", "&amp;&", "\x00&\r\n\t\ud800\udfff\U0010ffff",
        "a\u0301&\u2028\u2029\u200b\u202e\ufeff\ufffe",
        "amp; only", "one & two & three", "&" * 257,
        "x" * 65536 + "&amp;&" + "y" * 17,
        "&" + "x" * 65536,
    ]
    texts += [Text(s) for s in ("", "&", "&amp;&", "\x00&\ud800", "plain")]
    texts += list(TextEnum)
    return texts


def exercise(mod: ModuleType, text: str, calls: list[tuple[int, tuple]]) -> bool:
    value = mod.AmpersandText(text)
    model = "".join(text)
    if value.snapshot() != model:
        return True
    for attempts, actions in calls:
        target = expected(model) if attempts > 0 else model
        views = []
        index = 0

        def acknowledge() -> None:
            nonlocal index
            views.append(value.snapshot())
            action = actions[index] if index < len(actions) else None
            index += 1
            if action is not None:
                raise action("acknowledgement")

        try:
            value.deliver(acknowledge, attempts)
        except Exception:
            pass
        if value.snapshot() != target or any(view != target for view in views):
            return True
        model = target
    return False


def attack(mod: ModuleType) -> bool:
    scripts = (
        (),
        (TimeoutError,),
        (TimeoutError, TimeoutError),
        (TimeoutError,) * 5,
        (ValueError,),
        (OSError,),
        (RuntimeError,),
        (TimeoutError, ValueError),
        (TimeoutError, TimeoutError, OSError),
    )
    counts = (
        -10**100, -1, 0, 1, 2, 4, 10**100,
        False, True, Count(-2), Count(0), Count(3),
        Counts.NEGATIVE, Counts.ZERO, Counts.ONE, Counts.MANY,
        Flags.ZERO, Flags.ONE, Flags.ONE | Flags.TWO,
    )
    for text in samples():
        for actions in scripts:
            for count in counts:
                if exercise(mod, text, [(count, actions)]):
                    return True
        calls = [
            (0, ()),
            (-1, (TimeoutError,)),
            (3, (TimeoutError, ValueError)),
            (0, ()),
            (2, (TimeoutError,)),
            (1, (RuntimeError,)),
            (4, (TimeoutError,) * 5),
            (-10**100, ()),
            (1, ()),
        ]
        if exercise(mod, text, calls):
            return True
    return False
