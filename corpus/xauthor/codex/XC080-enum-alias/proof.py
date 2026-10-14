from __future__ import annotations

import ast
import importlib.util
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType


class PlainText(str):
    pass


class TextToken(str, Enum):
    PAYLOAD = '<img src=x onerror="alert(1)">'
    EMPTY = ""


def attack(mod: ModuleType) -> bool:
    texts = [
        '<img src=x onerror="alert(1)">',
        "",
        "x",
        "<script>alert(1)</script>",
        "'\"&<>",
        "\x00<img src=x onerror=alert(1)>",
        "\r\n",
        "한글",
        "e\u0301",
        "\ud800",
        "x" * 255,
        "x" * 256,
        "x" * 257,
        "x" * 65536,
    ]
    texts += [PlainText(text) for text in texts]
    texts += list(TextToken)
    styles = list(mod.CommentStyle.__members__.values())
    styles += [mod.CommentStyle[name] for name in mod.CommentStyle.__members__]
    styles += [mod.CommentStyle(style.value) for style in styles]
    target_code = mod._legacy_markup.__code__
    reached = False

    def observe(frame, event, arg):
        nonlocal reached
        if event == "call" and frame.f_code is target_code:
            reached = True

    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        for text in texts:
            for style in styles:
                try:
                    mod.render_comment(text, style)
                except Exception:
                    pass
            try:
                mod.render_comment(text)
            except Exception:
                pass
    finally:
        sys.setprofile(previous)
    return reached


def alias_barrier(source: str) -> bool:
    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]
    if {(node.module, tuple((x.name, x.asname) for x in node.names))
            for node in imports} != {
                ("enum", (("Enum", None),)),
                ("html", (("escape", None),)),
            }:
        return False
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(classes) != 1 or {node.name for node in functions} != {
        "_legacy_markup", "render_comment"
    }:
        return False
    if len(tree.body) != 6 or not isinstance(tree.body[0], ast.Expr):
        return False
    enum = classes[0]
    if enum.name != "CommentStyle" or enum.decorator_list or enum.keywords:
        return False
    if len(enum.bases) != 1 or ast.unparse(enum.bases[0]) != "Enum":
        return False
    values = {}
    for node in enum.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            return False
        if not isinstance(node.targets[0], ast.Name):
            return False
        if not isinstance(node.value, ast.Constant) or type(node.value.value) is not str:
            return False
        if node.targets[0].id in values:
            return False
        values[node.targets[0].id] = node.value.value
    if set(values) != {"TEXT", "LEGACY", "BADGE"}:
        return False
    if values["TEXT"] != values["LEGACY"]:
        return False
    renderer = next(node for node in functions if node.name == "render_comment")
    if renderer.decorator_list or len(renderer.body) != 4:
        return False
    first, legacy, badge, rejection = renderer.body
    for node, member in ((first, "TEXT"), (legacy, "LEGACY"), (badge, "BADGE")):
        if not isinstance(node, ast.If) or node.orelse or len(node.body) != 1:
            return False
        expected = ast.parse(f"style is CommentStyle.{member}", mode="eval").body
        if ast.dump(node.test) != ast.dump(expected):
            return False
        if not isinstance(node.body[0], ast.Return):
            return False
    if ast.unparse(legacy.body[0].value) != "_legacy_markup(text)":
        return False
    allowed = (
        ast.JoinedStr, ast.FormattedValue, ast.Constant, ast.Call, ast.Name, ast.Load
    )
    for branch in (first, badge):
        expression = branch.body[0].value
        if any(not isinstance(node, allowed) for node in ast.walk(expression)):
            return False
        for node in ast.walk(expression):
            if isinstance(node, ast.Call) and ast.unparse(node) != "escape(text)":
                return False
    return isinstance(rejection, ast.Raise)


if __name__ == "__main__":
    directory = Path(__file__).parent
    for filename, expected in (("decoy.py", False), ("twin.py", True)):
        path = directory / filename
        if alias_barrier(path.read_text(encoding="utf-8")) is expected:
            raise AssertionError(f"structural certificate: {filename}")
        spec = importlib.util.spec_from_file_location("alias_" + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if attack(module) is not expected:
            raise AssertionError(f"runtime attack: {filename}")
        payload = '<img src=x onerror="alert(1)">'
        output = module.render_comment(payload, module.CommentStyle.LEGACY)
        if (payload in output) is not expected:
            raise AssertionError(f"HTML injection: {filename}")
    print("AST barrier, runtime attack, and HTML injection checks passed")
