GUARD = """COMMAND_ROLES: Mapping[str, Sequence[str]] = MappingProxyType(
    {command: tuple(roles) for command, roles in BOOTSTRAP_ROLES.items()}
)"""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "outer mapping remains writable": [
        (GUARD, "COMMAND_ROLES = {command: tuple(roles) for command, roles in BOOTSTRAP_ROLES.items()}")
    ],
    "nested lists retain source aliases": [
        ("tuple(roles)", "roles")
    ],
    "nested copies remain writable": [
        ("tuple(roles)", "list(roles)")
    ],
    "empty role list left mutable": [
        ("tuple(roles)", "tuple(roles) if roles else roles")
    ],
    "singleton role list left mutable": [
        ("tuple(roles)", "roles if len(roles) == 1 else tuple(roles)")
    ],
    "multiple roles left mutable": [
        ("tuple(roles)", "roles if len(roles) > 1 else tuple(roles)")
    ],
    "authorization still consults bootstrap lists": [
        ("return role in COMMAND_ROLES.get(command, ())",
         "return role in BOOTSTRAP_ROLES.get(command, ())")
    ],
    "authorization uses bootstrap for absent commands": [
        ("return role in COMMAND_ROLES.get(command, ())",
         "return role in COMMAND_ROLES.get(command, BOOTSTRAP_ROLES.get(command, ()))")
    ],
}

MAPPING_METHODS = (
    "__setitem__", "__delitem__", "clear", "pop", "popitem",
    "update", "setdefault", "__ior__",
)
for hole in ("update", "setdefault", "pop", "clear", "__ior__"):
    blocked = "\n".join(
        "    " + method + " = _reject"
        for method in MAPPING_METHODS if method != hole
    )
    replacement = (
        "class LockedPolicy(dict):\n"
        "    def _reject(self, *args, **kwargs):\n"
        "        raise TypeError(\"locked\")\n"
        + blocked + "\n\n"
        "COMMAND_ROLES = LockedPolicy({command: tuple(roles) "
        "for command, roles in BOOTSTRAP_ROLES.items()})"
    )
    WEAKENED["mapping method left open: " + hole] = [(GUARD, replacement)]

LIST_METHODS = (
    "__setitem__", "__delitem__", "append", "extend", "insert",
    "pop", "remove", "clear", "__iadd__", "__imul__", "reverse", "sort",
)
for hole in ("__iadd__", "__imul__", "clear"):
    blocked = "\n".join(
        "    " + method + " = _reject"
        for method in LIST_METHODS if method != hole
    )
    replacement = (
        "class LockedRoles(list):\n"
        "    def _reject(self, *args, **kwargs):\n"
        "        raise ValueError(\"locked\")\n"
        + blocked + "\n\n"
        "COMMAND_ROLES = MappingProxyType({command: LockedRoles(roles) "
        "for command, roles in BOOTSTRAP_ROLES.items()})"
    )
    WEAKENED["nested method left open: " + hole] = [(GUARD, replacement)]

SAFE: dict[str, list[tuple[str, str]]] = {
    "unordered immutable role sets": [
        ("from collections.abc import Mapping, Sequence",
         "from collections.abc import Mapping, Collection as Sequence"),
        ("tuple(roles)", "frozenset(roles)"),
    ],
    "mapping proxy imported with alias": [
        ("from types import MappingProxyType", "from types import MappingProxyType as ReadOnly"),
        ("= MappingProxyType(", "= ReadOnly("),
    ],
    "mapping built from entry iterator": [
        ("{command: tuple(roles) for command, roles in BOOTSTRAP_ROLES.items()}",
         "dict((command, tuple(roles)) for command, roles in BOOTSTRAP_ROLES.items())"),
    ],
    "policy returns a mutable detached outer copy": [
        ("return COMMAND_ROLES", "return dict(COMMAND_ROLES)"),
    ],
    "policy returns mutable detached nested copies": [
        ("return COMMAND_ROLES",
         "return {command: list(roles) for command, roles in COMMAND_ROLES.items()}"),
    ],
    "policy exposes mutable bootstrap without affecting authorization": [
        ("return COMMAND_ROLES", "return BOOTSTRAP_ROLES"),
    ],
    "different rejection exception": [
        (GUARD,
         "class LockedPolicy(dict):\n"
         "    def _reject(self, *args, **kwargs):\n"
         "        raise ValueError(\"locked\")\n"
         + "\n".join("    " + method + " = _reject" for method in MAPPING_METHODS)
         + "\n\nCOMMAND_ROLES = MappingProxyType(LockedPolicy({command: tuple(roles) "
         "for command, roles in BOOTSTRAP_ROLES.items()}))"),
        ("return COMMAND_ROLES", "return LockedPolicy(COMMAND_ROLES)"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
