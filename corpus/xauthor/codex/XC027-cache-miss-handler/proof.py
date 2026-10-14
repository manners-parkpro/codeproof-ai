from __future__ import annotations

import ast
import builtins
import errno
import os
import shutil
from contextlib import ExitStack
from enum import Enum
from types import ModuleType
from unittest.mock import patch


class CachePath(str):
    pass


class NamedPath(str, Enum):
    CACHE = "/cache/session/item.bin"


class MissingChild(FileNotFoundError):
    pass


class ReadFailure(OSError):
    pass


PATHS = (
    "",
    ".",
    "..",
    "/",
    "item.bin",
    "/cache/session/item.bin",
    "/cache/../shared/item.bin",
    "/cache/한글/item.bin",
    "/cache/line\nitem.bin",
    "/cache/null\x00item.bin",
    "/cache/" + "x" * 8192,
    CachePath("/cache/subclass/item.bin"),
    NamedPath.CACHE,
)
ERRORS = (
    None,
    FileNotFoundError,
    MissingChild,
    OSError,
    ReadFailure,
    PermissionError,
    IsADirectoryError,
    NotADirectoryError,
    InterruptedError,
    ValueError,
    RuntimeError,
)
STAGES = ("open", "enter", "read", "exit")


def _error(kind, stage, path):
    if issubclass(kind, OSError):
        code = errno.ENOENT if issubclass(kind, FileNotFoundError) else errno.EIO
        return kind(code, stage, path)
    return kind(stage)


def _attempt(mod, path, stage, kind, exit_kind=None):
    deletions = []

    class Stream:
        def __enter__(self):
            if stage == "enter" and kind is not None:
                raise _error(kind, stage, path)
            return self

        def read(self):
            if stage == "read" and kind is not None:
                raise _error(kind, stage, path)
            return b"cached payload"

        def __exit__(self, exc_type, exc, traceback):
            active_kind = exit_kind or (kind if stage == "exit" else None)
            if active_kind is not None:
                raise _error(active_kind, "exit", path)
            return False

    def fake_open(*args, **kwargs):
        if stage == "open" and kind is not None:
            raise _error(kind, stage, path)
        return Stream()

    def fake_delete(*args, **kwargs):
        deletions.append((args, kwargs))

    original_open = builtins.open
    original_delete = shutil.rmtree
    with ExitStack() as stack:
        stack.enter_context(patch.object(builtins, "open", fake_open))
        stack.enter_context(patch.object(shutil, "rmtree", fake_delete))
        for name, value in list(vars(mod).items()):
            if value is original_open:
                stack.enter_context(patch.object(mod, name, fake_open))
            elif value is original_delete:
                stack.enter_context(patch.object(mod, name, fake_delete))
        try:
            mod.read_cached_blob(path)
        except Exception:
            pass
    return bool(deletions)


def attack(mod: ModuleType) -> bool:
    for path in PATHS:
        for stage in STAGES:
            for kind in ERRORS:
                if _attempt(mod, path, stage, kind):
                    return True
        for initial in ERRORS:
            for final in ERRORS[1:]:
                if _attempt(mod, path, "read", initial, final):
                    return True
    return False


def verify_structure(source: str) -> bool:
    tree = ast.parse(source)
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "read_cached_blob"
    ]
    if len(functions) != 1:
        return False
    function = functions[0]
    tries = [node for node in ast.walk(function) if isinstance(node, ast.Try)]
    if len(tries) != 1:
        return False
    guarded = tries[0]

    def caught_types(node):
        if node is None:
            return (BaseException,)
        if isinstance(node, ast.Tuple):
            return tuple(item for part in node.elts for item in caught_types(part))
        if isinstance(node, ast.Name):
            value = getattr(builtins, node.id, None)
            if isinstance(value, type) and issubclass(value, BaseException):
                return (value,)
        return ()

    previous = []
    unreachable = set()
    for handler in guarded.handlers:
        caught = caught_types(handler.type)
        if caught and all(
            any(issubclass(current, earlier) for earlier in previous)
            for current in caught
        ):
            unreachable.update(id(node) for node in ast.walk(handler))
        previous.extend(caught)
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    deletions = [
        node for node in calls
        if (
            isinstance(node.func, ast.Attribute) and node.func.attr == "rmtree"
        ) or (
            isinstance(node.func, ast.Name) and node.func.id == "rmtree"
        )
    ]
    return bool(deletions) and all(id(node) in unreachable for node in deletions)
