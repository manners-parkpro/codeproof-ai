from __future__ import annotations

import ast
import builtins
import io
import os
from contextlib import ExitStack
from enum import Enum, IntEnum
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


class PlainInt(int):
    pass


class PlainList(list):
    pass


class PlainStr(str):
    pass


class PlainBytes(bytes):
    pass


class SequenceNumber(IntEnum):
    BEFORE = -1
    START = 0
    NEXT = 1


class ArchiveName(str, Enum):
    RELATIVE = "../archive.bin"
    EMPTY = ""


AXES = {
    "empty": (0,),
    "singleton_and_nonpowers": (1, 2, 3, 7),
    "power_boundary": (8, 127, 128, 129, 255, 256, 257, 1025),
    "sign_and_multiples": "0, +/-1, +/-size, +/-size+/-1",
    "integer_width": "signed 64-bit boundaries and +/-2**4096",
    "subtypes": "bool, IntEnum, plain int/list/bytes/str, str Enum",
    "paths": "empty, relative, absolute, NUL, Unicode, long",
}


def _sequences(size: int):
    values = {
        -1, 0, 1, -2, 2, -127, -128, -129, 127, 128, 129,
        -(2**63) - 1, -(2**63), -(2**63) + 1,
        2**63 - 1, 2**63, 2**64, -(2**64),
        -(2**4096), 2**4096,
    }
    for factor in (1, 2, 3, 127):
        for delta in (-1, 0, 1):
            values.add(factor * size + delta)
            values.add(-factor * size + delta)
    yield from sorted(values)
    yield from (PlainInt(value) for value in sorted(values))
    yield from (False, True, *SequenceNumber)


def attack(mod: ModuleType) -> bool:
    opened = []

    def observe_open(*args, **kwargs):
        opened.append((args, kwargs))
        return io.BytesIO(b"archive-secret")

    paths = (
        "", "archive.bin", "../archive.bin", "/private-record.bin",
        "\x00", "archive\x00.bin", "\uac00\U0001f4be.bin", "a" * 4097,
        PlainStr("../plain.bin"), *ArchiveName,
    )
    sizes = (0, 1, 2, 3, 7, 8, 127, 128, 129, 255, 256, 257, 1025)
    original_opens = (builtins.open, io.open, os.open)
    with ExitStack() as stack:
        for name, value in tuple(vars(mod).items()):
            if any(value is original for original in original_opens):
                stack.enter_context(patch.object(mod, name, observe_open))
        stack.enter_context(patch("builtins.open", observe_open))
        stack.enter_context(patch("io.open", observe_open))
        stack.enter_context(patch("os.open", observe_open))
        for size in sizes:
            values = [b"", b"\x00", b"payload", PlainBytes(b"subtype")]
            payloads = [values[i % len(values)] for i in range(size)]
            for constructor in (list, PlainList):
                for sequence in _sequences(size):
                    for path in paths:
                        records = constructor(payloads)
                        try:
                            mod.read_record(records, sequence, path)
                        except Exception:
                            pass
                        if opened:
                            return True
    return False


def structural_certificate(source: str) -> bool:
    module = ast.parse(source)

    def same(node, statement):
        expected = ast.parse(statement).body[0]
        return ast.dump(node) == ast.dump(expected)

    nodes = [
        node for node in module.body
        if not same(node, "from io import open as archive_open")
    ]
    if len(nodes) != 2:
        return False
    doc, function = nodes
    if not (
        isinstance(doc, ast.Expr)
        and isinstance(doc.value, ast.Constant)
        and isinstance(doc.value.value, str)
        and isinstance(function, ast.FunctionDef)
        and function.name == "read_record"
        and not function.decorator_list
    ):
        return False
    signature = ast.parse(
        "def read_record(records: list[bytes], sequence: int, archive_path: str) -> bytes: pass"
    ).body[0]
    if (
        ast.dump(function.args) != ast.dump(signature.args)
        or ast.dump(function.returns) != ast.dump(signature.returns)
    ):
        return False
    body = list(function.body)
    if body and same(body[0], "records = tuple(records)"):
        body.pop(0)
    if len(body) != 5:
        return False
    length, empty, remainder, negative, result = body
    if not same(length, "size = len(records)"):
        return False
    bounds = {"size": (0, None)}
    if not (
        isinstance(empty, ast.If)
        and not empty.orelse
        and len(empty.body) == 1
        and any(
            ast.dump(empty.test) == ast.dump(ast.parse(test, mode="eval").body)
            for test in ("size == 0", "size <= 0")
        )
        and any(
            same(empty.body[0], exit_statement)
            for exit_statement in (
                'return b""',
                'raise LookupError("empty ring")',
                'raise RuntimeError("empty ring")',
            )
        )
    ):
        return False
    bounds["size"] = (bounds["size"][0] + 1, None)
    equivalent_remainders = (
        "index = sequence % size",
        "index = divmod(sequence, size)[1]",
        "index = sequence - (sequence // size) * size",
        "index = sequence % abs(size)",
        "index = int(sequence) % size",
    )
    if not any(same(remainder, statement) for statement in equivalent_remainders):
        return False
    if bounds["size"][0] <= 0:
        return False
    bounds["index"] = (0, None)
    if not (
        isinstance(negative, ast.If)
        and not negative.orelse
        and ast.dump(negative.test) == ast.dump(ast.parse("index < 0", mode="eval").body)
    ):
        return False
    if not same(result, "return records[index]"):
        return False
    return bounds["index"][0] >= negative.test.comparators[0].value


if __name__ == "__main__":
    folder = Path(__file__).parent
    source = (folder / "decoy.py").read_text(encoding="utf-8")
    if not structural_certificate(source):
        raise SystemExit("decoy structural certificate failed")
    if structural_certificate((folder / "twin.py").read_text(encoding="utf-8")):
        raise SystemExit("twin unexpectedly has the structural certificate")
    mutants = ast.parse((folder / "mutants.py").read_text(encoding="utf-8"))
    checked = 0
    for declaration in mutants.body:
        if declaration.target.id != "SAFE":
            continue
        for name, changes in ast.literal_eval(declaration.value).items():
            variant = source
            for old, new in changes:
                if variant.count(old) != 1:
                    raise SystemExit(f"{name}: ambiguous replacement")
                variant = variant.replace(old, new)
            if not structural_certificate(variant):
                raise SystemExit(f"{name}: safe variant lacks structural certificate")
            checked += 1
    print(f"AST: decoy and {checked} safe variants certified; twin rejected")
