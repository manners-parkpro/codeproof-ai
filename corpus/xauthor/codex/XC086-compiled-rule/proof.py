from copy import copy, deepcopy
from enum import Enum, IntEnum, StrEnum
from types import ModuleType
import re


class Text(str):
    pass


class Number(int):
    pass


class Label(str, Enum):
    VALID = "JOB-0000"
    INVALID = "job-0000"


class PlainLabel(StrEnum):
    VALID = "JOB-9999"
    INVALID = "JOB-１２３４"


class Flag(IntEnum):
    IGNORE_CASE = 2
    ASCII = 256


def expected(name: str) -> bool:
    return (
        len(name) == 8
        and name[:4] == "JOB-"
        and all("0" <= char <= "9" for char in name[4:])
    )


def probes() -> list[str]:
    values = {
        "", "JOB-", "JOB-0000", "JOB-0001", "JOB-1234", "JOB-9999",
        "job-0000", "Job-0000", "JOB-１２３４", "JOB-١٢٣٤", "JOB-²³⁴⁵",
        "JOB-0000\n", "JOB-0000\r\n", "\nJOB-0000", " JOB-0000",
        "JOB-0000 ", "JOB-0000\x00", "JOB-0000\u2028", "JOB-\ud800123",
        "JOB-0000tail", "prefixJOB-0000",
    }
    values.update("JOB-" + "0" * size for size in range(33))
    values.update("JOB-" + "9" * size for size in (63, 64, 65, 4096))
    original = "JOB-1234"
    for index in range(8):
        for char in ("a", "0", "9", "-", "_", "\n", "\x00", "９", "١", "İ"):
            values.add(original[:index] + char + original[index + 1:])
    ordered = sorted(values)
    return ordered + [Text(value) for value in ordered] + list(Label) + list(PlainLabel)


def broken(mod: ModuleType, exposed: list, names: list[str]) -> bool:
    try:
        current = [mod.RULE, mod.rule(), *exposed]
        for name in names:
            wanted = expected(name)
            if mod.accepts(name) is not wanted:
                return True
            for value in current:
                if (value.fullmatch(name) is not None) is not wanted:
                    return True
    except Exception:
        return True
    return False


def append_pattern(value) -> None:
    value.pattern += "|.*"


def repeat_pattern(value) -> None:
    value.pattern *= 0


def add_flags(value) -> None:
    value.flags |= re.IGNORECASE


def clear_flags(value) -> None:
    value.flags &= 0


def increment_flags(value) -> None:
    value.flags += 2


def attack(mod: ModuleType) -> bool:
    names = probes()
    exposed = [mod.RULE, mod.rule()]
    if broken(mod, exposed, names + [f"JOB-{number:04d}" for number in range(10000)]):
        return True

    for pattern, flags in ((".*", 0), ("[", -1), (Text("job-[0-9]{4}"), Flag.IGNORE_CASE)):
        try:
            draft = mod.NameRule(pattern, flags)
            draft.fullmatch("JOB-0000")
            draft.pattern = "x"
            draft.flags = True
        except Exception:
            pass
        if broken(mod, exposed, names):
            return True

    for original in list(exposed):
        for copier in (copy, deepcopy):
            try:
                result = copier(original)
            except Exception:
                result = None
            if result is not None:
                exposed.append(result)
            if broken(mod, exposed, names):
                return True

    patterns = [
        ".*", "", "[", "JOB-[0-9]{3}", "JOB-[0-9]{5}", "job-[0-9]{4}",
        Text(".*"), Label.VALID, PlainLabel.VALID,
        "JOB-(?P<serial>[0-9]{4})",
    ]
    flags = [
        re.IGNORECASE, 0, 2, True, False, Number(2), Flag.IGNORE_CASE,
        -1, -(10 ** 100), 10 ** 100, re.LOCALE, re.MULTILINE, re.ASCII,
    ]
    for target in [mod.BOOTSTRAP, *exposed]:
        operations = []
        for pattern in patterns:
            operations.append(lambda target=target, pattern=pattern: setattr(target, "pattern", pattern))
        for flag in flags:
            operations.append(lambda target=target, flag=flag: setattr(target, "flags", flag))
        operations.extend([
            lambda target=target: append_pattern(target),
            lambda target=target: repeat_pattern(target),
            lambda target=target: add_flags(target),
            lambda target=target: clear_flags(target),
            lambda target=target: increment_flags(target),
            lambda target=target: delattr(target, "pattern"),
            lambda target=target: setattr(target, "pattern", ".*"),
            lambda target=target: delattr(target, "flags"),
            lambda target=target: setattr(target, "flags", 2),
            lambda target=target: delattr(target, "flags"),
            lambda target=target: delattr(target, "pattern"),
        ])
        for operation in operations:
            try:
                operation()
            except Exception:
                pass
            if broken(mod, exposed, names):
                return True

    for mapping in (mod.BOOTSTRAP.__dict__, vars(mod.BOOTSTRAP)):
        operations = [
            lambda: mapping.__setitem__("pattern", ".*"),
            lambda: mapping.update(flags=2),
            lambda: mapping.__delitem__("pattern"),
            lambda: mapping.setdefault("pattern", ".*"),
            lambda: mapping.pop("flags", None),
            lambda: mapping.popitem(),
            lambda: mapping.clear(),
            lambda: mapping.__ior__({"pattern": "job-[0-9]{4}", "flags": Flag.IGNORE_CASE}),
            lambda: mapping.update(pattern="[", flags=10 ** 100),
        ]
        for operation in operations:
            try:
                operation()
            except Exception:
                pass
            if broken(mod, exposed, names):
                return True
    return False
