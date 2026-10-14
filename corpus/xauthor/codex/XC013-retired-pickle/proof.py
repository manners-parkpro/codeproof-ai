"""폐기된 역직렬화 경로 검증 - 호출 관찰과 무해한 실행 표식 및 AST 경로 검사를 결합한다."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from enum import Enum
import io
from pathlib import Path
import pickle
import sys
from types import ModuleType


_MARKER = "XC013-payload-executed"


class Text(str):
    pass


class Blob(bytes):
    pass


class Format(str, Enum):
    PICKLE = "pickle"
    JSON = "json"
    UTF8 = "utf8"


class _Payload:
    def __reduce__(self):
        return print, (_MARKER,)


def _probe(mod: ModuleType, payload: bytes, encoding: str) -> bool:
    entered = False

    def observe(frame, event, arg):
        nonlocal entered
        if event == "c_call" and arg is pickle.loads:
            entered = True

    output = io.StringIO()
    previous = sys.getprofile()
    try:
        with redirect_stdout(output):
            sys.setprofile(observe)
            try:
                mod.decode_record(payload, encoding)
            except Exception:
                pass
    finally:
        sys.setprofile(previous)
    return entered or _MARKER in output.getvalue()


def attack(mod: ModuleType) -> bool:
    payloads = [
        b"", b"null", b'"hello"', b"{}", b"\xff",
        b"x" * 65535, b"x" * 65536, b"x" * 65537,
    ]
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        encoded = pickle.dumps(_Payload(), protocol=protocol)
        payloads.extend((encoded, encoded + b"x" * 65536))
        payloads.append(pickle.dumps(42, protocol=protocol))
    names = [
        "pickle", "json", "utf8", "", "PICKLE", " pickle",
        "pickle ", "pickle\n", "pickle\x00", "x" * 4096,
    ]
    encodings = names + [Text(name) for name in names] + list(Format)
    broken = False
    for payload in payloads:
        for data in (payload, Blob(payload)):
            for encoding in encodings:
                broken = _probe(mod, data, encoding) or broken
    return broken


def certify_unreachable(source: str) -> bool:
    tree = ast.parse(source)
    if len(tree.body) != 4:
        return False
    if not (
        isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
        and ast.dump(tree.body[1]) == ast.dump(ast.parse("import json").body[0])
        and ast.dump(tree.body[2]) == ast.dump(ast.parse("import pickle").body[0])
    ):
        return False
    function = tree.body[3]
    if not (
        isinstance(function, ast.FunctionDef)
        and function.name == "decode_record"
        and not function.decorator_list
        and len(function.body) == 4
    ):
        return False
    guard, branch = function.body[:2]
    if not (
        isinstance(guard, ast.If)
        and not guard.orelse
        and len(guard.body) == 1
        and ast.dump(guard.body[0])
        == ast.dump(ast.parse('raise ValueError("unsupported encoding")').body[0])
        and isinstance(guard.test, ast.Compare)
        and isinstance(guard.test.left, ast.Name)
        and guard.test.left.id == "encoding"
        and len(guard.test.ops) == 1
        and isinstance(guard.test.ops[0], ast.NotIn)
        and len(guard.test.comparators) == 1
        and isinstance(guard.test.comparators[0], (ast.Tuple, ast.List, ast.Set))
    ):
        return False
    choices = guard.test.comparators[0].elts
    if not all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in choices):
        return False
    expected = ast.parse('if encoding == "pickle":\n    return pickle.loads(payload)').body[0]
    if ast.dump(branch) != ast.dump(expected):
        return False
    tail = ast.parse('if encoding == "json":\n    return json.loads(payload)\nreturn payload.decode("utf-8")').body
    if [ast.dump(node) for node in function.body[2:]] != [ast.dump(node) for node in tail]:
        return False
    return "pickle" not in {item.value for item in choices}


if __name__ == "__main__":
    directory = Path(__file__).resolve().parent
    for filename, expected in (("decoy.py", False), ("twin.py", True)):
        source = (directory / filename).read_text(encoding="utf-8")
        if certify_unreachable(source) is not (not expected):
            raise RuntimeError("unexpected structural certificate: " + filename)
        module = ModuleType("candidate")
        exec(compile(source, str(directory / filename), "exec"), module.__dict__)
        if attack(module) is not expected:
            raise RuntimeError("unexpected attack result: " + filename)
    print("AST certificate and decoy/twin attack contracts passed")
