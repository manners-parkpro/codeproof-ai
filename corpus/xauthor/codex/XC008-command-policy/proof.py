from __future__ import annotations

from enum import Enum
from operator import delitem, iadd, imul, ior, setitem
from types import ModuleType


EXPECTED = {
    "status": ("viewer", "operator", "admin"),
    "deploy": ("operator", "admin"),
    "purge": ("admin",),
    "disabled": (),
}


class Text(str):
    pass


class Command(str, Enum):
    STATUS = "status"
    PURGE = "purge"
    MISSING = "new"


class Role(str, Enum):
    ADMIN = "admin"
    GUEST = "guest"


def attack(mod: ModuleType) -> bool:
    commands = tuple(EXPECTED) + ("new", "", "\0", "명령", "x" * 4096)
    roles = ("viewer", "operator", "admin", "guest", "", "\0", "역할", "r" * 4096)
    command_values = commands + tuple(map(Text, commands)) + tuple(Command)
    role_values = roles + tuple(map(Text, roles)) + tuple(Role)

    def changed() -> bool:
        try:
            for command in command_values:
                for role in role_values:
                    expected = role in EXPECTED.get(command, ())
                    if mod.allowed(command, role) is not expected:
                        return True
        except Exception:
            return True
        return False

    def attempt(operation) -> bool:
        try:
            operation()
        except Exception:
            pass
        return changed()

    def alter_values(values) -> bool:
        operations = (
            lambda: values.append("guest"),
            lambda: values.extend(["guest"]),
            lambda: values.insert(0, "guest"),
            lambda: setitem(values, 0, "guest"),
            lambda: setitem(values, slice(None), ["guest"]),
            lambda: delitem(values, 0),
            lambda: delitem(values, slice(None)),
            lambda: values.pop(),
            lambda: values.remove("admin"),
            lambda: values.clear(),
            lambda: iadd(values, ["guest"]),
            lambda: iadd(values, ("guest",)),
            lambda: imul(values, 0),
            lambda: values.add("guest"),
            lambda: values.update(["guest"]),
            lambda: values.discard("admin"),
            lambda: values.difference_update(["admin"]),
        )
        return any(attempt(operation) for operation in operations)

    def alter_mapping(mapping) -> bool:
        for command in commands:
            operations = (
                lambda: setitem(mapping, command, ["guest"]),
                lambda: delitem(mapping, command),
                lambda: mapping.update({command: ["guest"]}),
                lambda: mapping.setdefault(command, ["guest"]),
                lambda: mapping.pop(command),
                lambda: ior(mapping, {command: ["guest"]}),
            )
            if any(attempt(operation) for operation in operations):
                return True
        return any(attempt(operation) for operation in (
            lambda: mapping.popitem(),
            lambda: mapping.clear(),
        ))

    if changed():
        return True
    source = mod.BOOTSTRAP_ROLES
    saved_items = tuple(source.items())
    saved_contents = [(values, list(values)) for _, values in saved_items]
    try:
        for mapping in (mod.COMMAND_ROLES, mod.policy()):
            for command in EXPECTED:
                for values in (mapping[command], mapping.get(command)):
                    if alter_values(values):
                        return True
            for values in tuple(mapping.values()):
                if alter_values(values):
                    return True
            for _, values in tuple(mapping.items()):
                if alter_values(values):
                    return True
            if alter_mapping(mapping):
                return True
        for _, values in saved_items:
            if alter_values(values):
                return True
        if alter_mapping(source):
            return True
        for _, values in saved_items:
            if alter_values(values):
                return True
        return changed()
    finally:
        for values, original in saved_contents:
            values[:] = original
        source.clear()
        source.update(saved_items)
