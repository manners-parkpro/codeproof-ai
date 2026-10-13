from __future__ import annotations

import ast
from enum import Enum, StrEnum
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


class Text(str):
    pass


class Labels(list):
    pass


class MixedText(str, Enum):
    RUN = "run"
    EMPTY = ""


class StandardText(StrEnum):
    RUN = "run"


class ShellAttempt(Exception):
    pass


def attack(mod: ModuleType) -> bool:
    commands = [
        "",
        "run",
        "printf preview",
        "printf preview; printf injected",
        "$(printf injected)",
        "line1\nline2",
        "\x00",
        "한글/\U0001f680",
        "\ud800",
        "x" * 65537,
        Text("run"),
        Text(""),
        MixedText.RUN,
        MixedText.EMPTY,
        StandardText.RUN,
    ]
    label_sets = [
        [],
        [""],
        ["run"],
        ["display"],
        ["before", "run"],
        ["run", "after"],
        ["same", "same"],
        ["a"] * 1025,
        ["x" * 65537],
        ["\x00", "\n", "\ud800"],
        ["한글", "\U0001f680"],
        [Text("run")],
        [MixedText.RUN],
        [StandardText.RUN],
        Labels(),
        Labels(["run"]),
    ]
    attempted = False

    def intercept(*args, **kwargs):
        nonlocal attempted
        attempted = True
        raise ShellAttempt

    with patch("subprocess.Popen", side_effect=intercept):
        for command in commands:
            for labels in label_sets:
                current = type(labels)(labels)
                try:
                    mod.preview_job(command, current)
                except Exception:
                    pass
                if attempted:
                    return True
    return False


def check_structure(source: str) -> None:
    tree = ast.parse(source)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert set(functions) == {"_plan", "preview_job"}
    assert all(
        isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))
        or isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
        for n in tree.body
    )
    planner = functions["_plan"]
    assert not planner.decorator_list
    body = list(planner.body)
    if isinstance(body[0], ast.If):
        rejection = body.pop(0)
        assert ast.dump(rejection.test) == ast.dump(ast.parse('command == ""', mode="eval").body)
        assert not rejection.orelse
        assert len(rejection.body) == 1 and isinstance(rejection.body[0], ast.Raise)
        exc = rejection.body[0].exc
        assert isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name)
        assert exc.func.id in {"ValueError", "RuntimeError"}
        assert all(isinstance(arg, ast.Constant) for arg in exc.args)
        assert not exc.keywords
    assert len(body) == 2
    loop, completion = body
    assert isinstance(loop, ast.For) and not loop.orelse
    assert isinstance(loop.target, ast.Name) and loop.target.id == "label"
    assert isinstance(loop.iter, ast.Name) and loop.iter.id == "labels"
    assert len(loop.body) == 1 and isinstance(loop.body[0], ast.Expr)
    event = loop.body[0].value
    assert isinstance(event, ast.Yield)
    assert isinstance(event.value, (ast.Tuple, ast.List))
    assert len(event.value.elts) == 2
    tag, value = event.value.elts
    assert isinstance(tag, ast.Constant) and isinstance(tag.value, str)
    assert tag.value != "run"
    assert isinstance(value, ast.Name) and value.id == "label"
    assert isinstance(completion, ast.Return)
    assert all(
        isinstance(n, (ast.Tuple, ast.List, ast.Constant, ast.Name, ast.Load))
        for n in ast.walk(completion.value)
    )
    consumer = functions["preview_job"]
    assert not consumer.decorator_list
    assert len(consumer.body) == 3
    init, consume, result = consumer.body
    assert ast.dump(init) == ast.dump(ast.parse("lines = []").body[0])
    assert ast.dump(result) == ast.dump(ast.parse("return lines").body[0])
    assert isinstance(consume, ast.For) and not consume.orelse
    assert ast.dump(consume.target) == ast.dump(ast.parse("for kind, value in ():\n    pass").body[0].target)
    assert ast.dump(consume.iter) == ast.dump(ast.parse("_plan(command, labels)", mode="eval").body)
    assert len(consume.body) == 1 and isinstance(consume.body[0], ast.If)
    dispatch = consume.body[0]
    assert ast.dump(dispatch.test) == ast.dump(ast.parse('kind == "run"', mode="eval").body)
    assert ast.dump(ast.Module(body=dispatch.orelse, type_ignores=[])) == ast.dump(ast.parse("lines.append(value)"))
    assert len(dispatch.body) == 1 and isinstance(dispatch.body[0], ast.Expr)
    assert isinstance(dispatch.body[0].value, ast.Call)


if __name__ == "__main__":
    import runpy

    directory = Path(__file__).resolve().parent
    original = (directory / "decoy.py").read_text(encoding="utf-8")
    check_structure(original)
    variants = runpy.run_path(str(directory / "mutants.py"))
    for name, replacements in variants["SAFE"].items():
        source = original
        for old, new in replacements:
            assert source.count(old) == 1, name
            source = source.replace(old, new)
        check_structure(source)
    try:
        check_structure((directory / "twin.py").read_text(encoding="utf-8"))
    except AssertionError:
        pass
    else:
        raise AssertionError("twin must violate the generator structure")
    print("AST: decoy and all SAFE variants proved; twin rejected")
