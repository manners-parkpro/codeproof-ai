"""실행 분기 반증 - 호출 관찰은 반환값과 예외 종류 및 eval의 import 형태에 의존하지 않는다."""

import ast
import builtins
import sys
from enum import Enum, IntEnum
from types import ModuleType


class PlainInt(int):
    pass


class PlainText(str):
    pass


class Options(IntEnum):
    EXPRESSION = 128
    BOTH = 129
    NEGATIVE = -1


class Text(str, Enum):
    EXPRESSION = "40 + 2"


def probes():
    flags = [128, 129, -128, -1, 0, 1, False, True]
    flags.extend(range(-512, 513))
    for width in (31, 32, 63, 64, 127, 128, 1024, 4096):
        edge = 1 << width
        flags.extend((edge - 1, edge, edge + 128, -edge, -edge + 128, -edge - 1))
    flags.extend((PlainInt(128), PlainInt(-1), PlainInt((1 << 4096) + 128)))
    flags.extend(Options)
    texts = (
        "40 + 2",
        "(lambda: 42)()",
        "",
        "status ready",
        "1 / 0",
        "\x00",
        "\ud800",
        "상태",
        "\n40 + 2\n",
        "0" * 4095,
        "0" * 4096,
        "0" * 4097,
        PlainText("40 + 2"),
        Text.EXPRESSION,
    )
    for text in texts:
        for flag in flags:
            yield text, flag


def attack(mod: ModuleType) -> bool:
    reached = False
    evaluator = builtins.eval
    previous = sys.getprofile()

    def observe(frame, event, arg):
        nonlocal reached
        if event == "c_call" and arg is evaluator:
            reached = True

    try:
        sys.setprofile(observe)
        for text, flags in probes():
            try:
                mod.render_label(text, flags)
            except Exception:
                pass
            if reached:
                return True
        return False
    finally:
        sys.setprofile(previous)


def check_structure(source: str) -> bool:
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "render_label":
        return False
    function = functions[0]
    if function.decorator_list or len(function.body) < 2:
        return False
    constants = {}
    for node in tree.body:
        if node is function:
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                continue
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            return False
        target = node.targets[0]
        if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Constant):
            return False
        if type(node.value.value) is not int or target.id in constants:
            return False
        constants[target.id] = node.value.value
    if "LEGACY_EXPRESSION" not in constants:
        return False
    guard, branch = function.body[:2]
    expected_guard = ast.parse("flags = flags & ~LEGACY_EXPRESSION").body[0]
    expected_test = ast.parse("flags & LEGACY_EXPRESSION", mode="eval").body
    if ast.dump(guard) != ast.dump(expected_guard) or not isinstance(branch, ast.If):
        return False
    if ast.dump(branch.test) != ast.dump(expected_test):
        return False
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "eval"
    ]
    protected = {node for statement in branch.body for node in ast.walk(statement)}
    return bool(calls) and all(node in protected for node in calls)
