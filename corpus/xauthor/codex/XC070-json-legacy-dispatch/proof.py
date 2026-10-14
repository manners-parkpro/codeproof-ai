"""도달성 반증 - JSON 값의 종류, 표기, 크기, 오류 및 문자열 하위 타입을 탐침한다."""

import ast
import json
import subprocess
import sys
from contextlib import ExitStack
from enum import Enum, StrEnum
from types import ModuleType
from unittest.mock import patch


class PlainText(str):
    pass


COMMAND = "printf XC070_PROBE"


def documents() -> list[str]:
    values = [
        None, False, True, 0, 1, -1, 2**256, -(2**256),
        0.0, -0.0, 1.5, -1.5, 1.7976931348623157e308,
        5e-324, float("inf"), float("-inf"), float("nan"),
        "", COMMAND, [], [COMMAND], {}, {"command": COMMAND},
        {"command": COMMAND, "extra": 0},
        {"__class__": "_ShellPreview", "command": COMMAND},
        {"__type__": "_ShellPreview", "command": COMMAND},
        {"outer": {"command": COMMAND}},
        [{"command": COMMAND}],
        {"command": [COMMAND]}, {"command": None},
    ]
    result = [json.dumps(value) for value in values]
    result += [
        "", " ", "\t\r\n", "{", "[", "null trailing", "'command'",
        '{"command":', "\ufeff{}", "\x00",
        '{"command":"printf XC070_PROBE","command":"printf XC070_SECOND"}',
        r'{"\u0063ommand":"printf XC070_PROBE"}',
        r'"\ud800"', r'"\u2028"', r'"\u0000"',
        "1e10000", "-1e10000", "1e-10000", "-0", "0e0",
        "9" * 5000, "-" + "9" * 5000,
        json.dumps(COMMAND * 4096),
        json.dumps([0] * 4096),
        json.dumps({str(i): i for i in range(1024)}),
        "[" * (sys.getrecursionlimit() + 32) + "0" + "]" * (sys.getrecursionlimit() + 32),
    ]
    for depth in (1, 2, 8, 64):
        result.append("[" * depth + '{"command":"' + COMMAND + '"}' + "]" * depth)
    for padding in (" ", "\t", "\r\n"):
        result.append(padding + '{"command":"' + COMMAND + '"}' + padding)
    return result


def attack(mod: ModuleType) -> bool:
    reached = False
    original = subprocess.check_output

    def intercepted(*args, **kwargs):
        nonlocal reached
        reached = True
        return "XC070_INTERCEPTED"

    with ExitStack() as stack:
        stack.enter_context(patch.object(subprocess, "check_output", intercepted))
        for name, value in list(vars(mod).items()):
            if value is original:
                stack.enter_context(patch.object(mod, name, intercepted))
        for document in documents():
            MixedText = Enum("MixedText", {"VALUE": document}, type=str)
            StandardText = StrEnum("StandardText", {"VALUE": document})
            for candidate in (
                document, PlainText(document), MixedText.VALUE, StandardText.VALUE
            ):
                try:
                    mod.preview_step(candidate)
                except Exception:
                    pass
                if reached:
                    return True
    return False


def structural_barrier(source: str) -> bool:
    tree = ast.parse(source)
    if not tree.body or not isinstance(tree.body[0], ast.Expr):
        return False
    if not isinstance(tree.body[0].value, ast.Constant):
        return False
    if not isinstance(tree.body[0].value.value, str):
        return False
    aliases = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name not in ("json", "subprocess"):
                    return False
                aliases[item.asname or item.name] = item.name
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                if node.level or (node.module, item.name) not in (
                    ("json", "loads"), ("json", "JSONDecoder"),
                    ("subprocess", "check_output"), ("dataclasses", "dataclass"),
                ):
                    return False
                aliases[item.asname or item.name] = node.module + "." + item.name

    def qualified(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return qualified(node.value) + "." + node.attr
        return ""

    def equivalent(node, expression):
        return ast.dump(node) == ast.dump(ast.parse(expression, mode="eval").body)

    def json_return(node):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
            return False
        call = node.value
        function = qualified(call.func)
        if isinstance(call.func, ast.Attribute) and call.func.attr == "decode":
            owner = call.func.value
            if (
                isinstance(owner, ast.Call)
                and qualified(owner.func) == "json.JSONDecoder"
                and not owner.args and not owner.keywords
            ):
                function = "json.loads"
        if function != "json.loads":
            return False
        if len(call.args) != 1 or not equivalent(call.args[0], "document"):
            return False
        return all(
            item.arg in ("object_hook", "object_pairs_hook")
            and equivalent(item.value, "dict")
            for item in call.keywords
        )

    definitions = {node.name: node for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    if set(definitions) != {"_ShellPreview", "_decode_step", "preview_step"}:
        return False
    cls = definitions["_ShellPreview"]
    if cls.bases or cls.keywords or cls.type_params or len(cls.body) != 1:
        return False
    if ast.dump(cls.body[0]) != ast.dump(ast.parse("command: str").body[0]):
        return False
    if len(cls.decorator_list) != 1:
        return False
    decorator = cls.decorator_list[0]
    if (
        not isinstance(decorator, ast.Call)
        or qualified(decorator.func) != "dataclasses.dataclass"
        or not equivalent(decorator, "dataclass(frozen=True)")
    ):
        return False
    decoder = definitions["_decode_step"]
    for name, result in (("_decode_step", "object"), ("preview_step", "str")):
        function = definitions[name]
        signature = ast.parse(f"def {name}(document: str) -> {result}: pass").body[0]
        if (
            ast.dump(function.args) != ast.dump(signature.args)
            or function.returns is None
            or ast.dump(function.returns) != ast.dump(signature.returns)
            or function.type_params
        ):
            return False
    if decoder.decorator_list or len(decoder.body) != 1:
        return False
    body = decoder.body[0]
    if isinstance(body, ast.Try):
        if body.orelse or body.finalbody or len(body.body) != 1:
            return False
        if len(body.handlers) != 1:
            return False
        handler = body.handlers[0]
        if not equivalent(handler.type, "ValueError"):
            return False
        if len(handler.body) != 1 or not isinstance(handler.body[0], ast.Raise):
            return False
        if not equivalent(handler.body[0].exc, 'RuntimeError("invalid document")'):
            return False
        if handler.name != "exc" or not equivalent(handler.body[0].cause, "exc"):
            return False
        body = body.body[0]
    if not json_return(body):
        return False
    preview = definitions["preview_step"]
    if preview.decorator_list or len(preview.body) != 3:
        return False
    assignment, branch, output = preview.body
    if ast.dump(assignment) != ast.dump(ast.parse("step = _decode_step(document)").body[0]):
        return False
    if not isinstance(branch, ast.If) or branch.orelse:
        return False
    if not (
        equivalent(branch.test, "isinstance(step, _ShellPreview)")
        or equivalent(branch.test, "type(step) is _ShellPreview")
    ):
        return False
    if len(branch.body) != 1 or not isinstance(branch.body[0], ast.Return):
        return False
    sink = branch.body[0].value
    if not isinstance(sink, ast.Call) or qualified(sink.func) != "subprocess.check_output":
        return False
    if len(sink.args) != 1 or not equivalent(sink.args[0], "step.command"):
        return False
    if len(sink.keywords) != 2 or {item.arg for item in sink.keywords} != {"shell", "text"}:
        return False
    if not all(equivalent(item.value, "True") for item in sink.keywords):
        return False
    if not isinstance(output, ast.Return) or not isinstance(output.value, ast.Call):
        return False
    if qualified(output.value.func) != "json.dumps":
        return False
    if len(output.value.args) != 1 or not equivalent(output.value.args[0], "step"):
        return False
    if len(output.value.keywords) != 2:
        return False
    if {item.arg for item in output.value.keywords} != {"ensure_ascii", "sort_keys"}:
        return False
    if not all(
        equivalent(item.value, "True") or equivalent(item.value, "False")
        for item in output.value.keywords
    ):
        return False
    allowed = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)
    if any(not isinstance(node, allowed) for node in tree.body[1:]):
        return False
    names = {
        "_ShellPreview", "_decode_step", "preview_step", "dict", "type", "isinstance",
        "str", "object", "document", "step", "ValueError", "RuntimeError", "exc",
    }
    if names.intersection(aliases):
        return False
    return True


def verify_structure() -> None:
    import runpy
    from pathlib import Path

    directory = Path(__file__).parent
    source = (directory / "decoy.py").read_text(encoding="utf-8")
    twin = (directory / "twin.py").read_text(encoding="utf-8")
    if not structural_barrier(source) or structural_barrier(twin):
        raise AssertionError("decoy/twin structural barrier")
    variants = runpy.run_path(str(directory / "mutants.py"))
    for kind in ("SAFE", "WEAKENED"):
        for name, edits in variants[kind].items():
            candidate = source
            for old, new in edits:
                if candidate.count(old) != 1:
                    raise AssertionError((name, "ambiguous replacement"))
                candidate = candidate.replace(old, new)
            if structural_barrier(candidate) != (kind == "SAFE"):
                raise AssertionError((kind, name))
    print(
        f"AST barrier: decoy + {len(variants['SAFE'])} safe variants certified; "
        f"twin + {len(variants['WEAKENED'])} weakened variants rejected."
    )


if __name__ == "__main__":
    verify_structure()
