WEAKENED: dict[str, list[tuple[str, str]]] = {
    "empty updates alias": [
        ("working = source.copy()", "working = source.copy() if bindings else source"),
    ],
    "missing lookup mutates source": [
        ("working = source.copy()", "working = source if any(v.name == 'missing' for v in required) else source.copy()"),
    ],
    "forget all initial bindings": [
        ("working = source.copy()", "working = Context()"),
    ],
    "forget unrelated bindings": [
        ("working = source.copy()", "working = Context()\n    for variable, value in source.items():\n        if variable in required:\n            working.run(variable.set, value)"),
    ],
    "reverse assignment order": [
        ("for variable, value in bindings:", "for variable, value in reversed(bindings):"),
    ],
    "keep first repeated assignment": [
        ("for variable, value in bindings:\n        variable.set(value)", "seen = set()\n    for variable, value in bindings:\n        if variable not in seen:\n            variable.set(value)\n            seen.add(variable)"),
    ],
    "merge distinct variables with same name": [
        ("for variable, value in bindings:\n        variable.set(value)", "by_name = {}\n    for variable, value in bindings:\n        by_name.setdefault(variable.name, variable).set(value)"),
    ],
    "suppress missing values and defaults": [
        ("variable.get() for variable in required", "variable.get('') for variable in required"),
    ],
    "ignore default values": [
        ("variable.get() for variable in required", "__import__('contextvars').copy_context()[variable] for variable in required"),
    ],
    "materialize defaults as bindings": [
        ("return tuple(variable.get() for variable in required)", "values = tuple(variable.get() for variable in required)\n    for variable, value in zip(required, values):\n        variable.set(value)\n    return values"),
    ],
    "return initial snapshot": [
        ("return values, working", "return values, source.copy()"),
    ],
    "return source after isolated computation": [
        ("return values, working", "return values, source"),
    ],
    "run assignments in ambient context": [
        ("values = working.run(_apply, bindings, required)", "values = _apply(bindings, required)"),
    ],
    "reject entered source": [
        ("working = source.copy()", "working = source.run(source.copy)"),
    ],
    "drop empty request snapshot": [
        ("return values, working", "return values, working if required else Context()"),
    ],
    "cap assignment count": [
        ("for variable, value in bindings:", "for variable, value in bindings[:128]:"),
    ],
    "cap required count": [
        ("variable.get() for variable in required", "variable.get() for variable in required[:128]"),
    ],
    "coerce string subtype values": [
        ("variable.set(value)", "variable.set(str(value))"),
    ],
    "ignore empty string assignment": [
        ("variable.set(value)", "if value:\n            variable.set(value)"),
    ],
    "assert missing lookup rejection": [
        ("return tuple(variable.get() for variable in required)", "values = []\n    for variable in required:\n        try:\n            values.append(variable.get())\n        except LookupError:\n            assert False\n    return tuple(values)"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "unbound copy method": [
        ("source.copy()", "Context.copy(source)"),
    ],
    "rebuild bindings explicitly": [
        ("working = source.copy()", "working = Context()\n    for variable, value in source.items():\n        working.run(variable.set, value)"),
    ],
    "different rejection exception": [
        ("values = working.run(_apply, bindings, required)", "try:\n        values = working.run(_apply, bindings, required)\n    except LookupError as error:\n        raise ValueError('missing setting') from error"),
    ],
    "list of read values": [
        ("return tuple(variable.get() for variable in required)", "return [variable.get() for variable in required]"),
    ],
    "extra return copy": [
        ("return values, working", "return values, working.copy()"),
    ],
    "collapse updates by variable identity": [
        ("for variable, value in bindings:", "for variable, value in dict(bindings).items():"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
