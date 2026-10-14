from enum import Enum, IntEnum
from types import ModuleType


class Text(str):
    pass


class Label(str, Enum):
    EMPTY = ""
    EVENT = "enum-event"
    BODY = "enum-body"


class Count(IntEnum):
    ONE = 1
    FOUR = 4


def attack(mod: ModuleType) -> bool:
    journal = mod.EventJournal()
    expected: dict[str, str] = {}
    broken = False

    def matches() -> bool:
        rows = list(journal.entries())
        return len(rows) == len(expected) and dict(rows) == expected

    def send(key, body, failures=0, attempts=3, error=TimeoutError, direct=False):
        nonlocal broken
        expected.setdefault(key, body)
        remaining = failures

        def acknowledge():
            nonlocal remaining, broken
            if not matches():
                broken = True
            if remaining:
                remaining -= 1
                raise error("acknowledgement lost")

        try:
            if direct:
                journal.record(key, body, acknowledge)
            else:
                mod.deliver(journal, key, body, acknowledge, attempts)
        except Exception:
            pass
        if not matches():
            broken = True

    try:
        send("first", "original", failures=2)
        send("first", "replacement", failures=3)
        send("second", "original")
        send("", "", failures=2, attempts=Count.FOUR)
        send(Label.EMPTY, "changed-empty", direct=True)
        send("nul", "prefix")
        send("nul\x00suffix", "nul\x00body", failures=1)
        send("nul\x00other", "prefix")
        send("Case", "upper")
        send("case", "lower")
        send("\u00e9", "composed")
        send("e\u0301", "decomposed")
        send("\ud800", "\udfff", failures=1)
        send("\ud801", "\udffe", direct=True)
        send("\ufffd", "\U0010ffff")
        send("\U0001f600", "\x00\n\t")
        send(Text("subclass"), Text("subclass-body"), failures=2)
        send("subclass", "new")
        send(Label.EVENT, Label.BODY, failures=1)
        send("enum-event", "new-enum", direct=True)
        send("x" * 4096 + "a", "p" * 4097, failures=2)
        send("x" * 4096 + "b", "p" * 4097)
        send("retry-exhausted", "committed", failures=10, attempts=Count.FOUR)
        send("retry-exhausted", "changed", attempts=True)
        send("sync-error", "committed-before-error", failures=1, error=OSError)
        send("direct-error", "committed-before-error", failures=1, error=ValueError, direct=True)
        send("direct-error", "new", direct=True)
        send("single-attempt", "one", failures=1, attempts=Count.ONE)
        for index in range(80):
            send(f"prior-{index}", f"body-{index}", failures=index % 4, attempts=4)
        for index in reversed(range(80)):
            send(f"prior-{index}", f"changed-{index}", failures=1)
        for invalid in (0, -1, -(10 ** 100), False):
            try:
                mod.deliver(journal, "rejected", "unused", lambda: None, invalid)
            except Exception:
                pass
            if not matches():
                broken = True
        return broken
    finally:
        journal.close()
