"""열 색인 계약의 반증 - 유효성과 위치 보존 및 입력 불변성을 함께 확인한다."""

from enum import Enum
from itertools import product
from types import ModuleType
from unicodedata import normalize


class Header(str):
    pass


class HeaderList(list):
    pass


class NamedHeader(str, Enum):
    TITLE = " Title "
    OTHER = "Other"


def _cases() -> list[list[str]]:
    cases = [
        [],
        ["Name"],
        ["z", "a", "m"],
        [" Name ", "AGE", "Ｃｉｔｙ"],
        ["x", "y", "x"],
        ["x", "x", "x"],
        ["x", "y", "y"],
        ["x", "X"],
        ["x", " x "],
        ["A", "Ａ"],
        ["Straße", "STRASSE"],
        ["\u00e9", "e\u0301"],
        ["\ufb03", "ffi"],
        ["\u03c2", "\u03c3"],
        ["\u00a8", "\u0308"],
        ["\u03d2", "\u03c5"],
        ["\u00a8"],
        ["\u03d2"],
        ["a b", "ab"],
        ["a  b", "a b"],
        ["\x00", "\uffff", "\ud800", "\udfff", "\u200b"],
        ["a" * 10000, "a" * 10000 + "b"],
        [Header(" Mixed "), Header("Other")],
        [Header(" Mixed "), "mixed"],
        [NamedHeader.TITLE, NamedHeader.OTHER],
        [NamedHeader.TITLE, "title"],
        HeaderList(["Z", "A"]),
        HeaderList(["Z", "z"]),
        HeaderList([]),
    ]
    for blank in ("", " ", "\t\r\n", "\u00a0", "\u2003", "\u3000", "\x1c"):
        for position in range(4):
            row = ["a", "b", "c"]
            row.insert(position, blank)
            cases.append(row)
    for size in (2, 3, 31, 256, 257, 513):
        row = [f"column-{index}" for index in range(size)]
        cases.append(row)
        for position in (0, size // 2, size - 1):
            blank_row = row.copy()
            blank_row[position] = ""
            cases.append(blank_row)
        for target in (0, size // 2):
            collision = row.copy()
            collision[-1] = " " + collision[target].upper() + " "
            cases.append(collision)
    alphabet = ("a", "A", " b ", "b", "", "\u00a0", "\u00df", "ss")
    for width in range(4):
        cases.extend(list(row) for row in product(alphabet, repeat=width))
    return cases


def attack(mod: ModuleType) -> bool:
    for headers in _cases():
        original = tuple(headers)
        canonical = [normalize("NFKC", name).strip().casefold() for name in original]
        invalid = any(key == "" for key in canonical) or any(
            key in canonical[:index] for index, key in enumerate(canonical)
        )
        expected = dict(zip(canonical, range(len(canonical))))
        for _ in range(2):
            rejected = False
            result = None
            try:
                result = mod.header_positions(headers)
            except Exception:
                rejected = True
            if len(headers) != len(original) or any(
                actual is not before for actual, before in zip(headers, original)
            ):
                return True
            if invalid:
                if not rejected:
                    return True
            elif rejected or not isinstance(result, dict) or result != expected:
                return True
    return False
