from contextvars import Context, ContextVar, copy_context
from enum import Enum
from itertools import product
from types import ModuleType


class Text(str):
    pass


class Items(tuple):
    pass


class Choice(str, Enum):
    BLUE = "blue"


def _same(context, snapshot):
    actual = dict(context.items())
    return actual.keys() == snapshot.keys() and all(
        actual[key] is value for key, value in snapshot.items()
    )


def _reference(snapshot, bindings, required):
    expected = dict(snapshot)
    for variable, value in bindings:
        expected[variable] = value
    values = []
    for variable in required:
        if variable in expected:
            values.append(expected[variable])
        else:
            try:
                values.append(Context().run(variable.get))
            except LookupError:
                return expected, None
    return expected, values


def _case(mod, initial, scenario, entered, subtype):
    x = ContextVar("setting")
    y = ContextVar("setting")
    default = Text("default")
    d = ContextVar("default", default=default)
    missing = ContextVar("missing")
    spare = ContextVar("unrelated")
    absent = ContextVar("later")
    many = tuple(ContextVar(str(i)) for i in range(137))
    old, new, last = Text("old"), Text("new"), Text("last")
    source = Context()
    history = []
    if initial:
        history.append((x, source.run(x.set, old)))
        history.append((x, source.run(x.set, Text("replaced"))))
        source.run(y.set, Text("other"))
        source.run(d.set, Text("explicit"))
        source.run(spare.set, ["shared value, independent binding"])
    if initial == 2:
        for variable in many:
            source.run(variable.set, Text(variable.name))
        token = source.run(missing.set, "temporary")
        source.run(missing.reset, token)
    cases = [
        ((), ()),
        ((), (d,)),
        (((x, new),), (x, d, x)),
        (((x, new), (x, last), (y, old)), (x, y, d)),
        (((x, new), (y, last)), (x, missing)),
        ((), (missing,)),
        (((missing, ""), (d, Choice.BLUE)), (missing, d)),
        (((y, Choice.BLUE), (x, Text("z" * 8193))), (y, x)),
        (tuple((v, Text(str(i))) for i, v in enumerate(many)), many),
        (tuple((x, Text(str(i))) for i in range(257)), (x,) * 131),
        (((x, new),), (y,)),
        (((x, new), (x, "")), (x,)),
    ]
    bindings, required = cases[scenario]
    if subtype:
        bindings = Items(Items(pair) for pair in bindings)
        required = Items(required)
    before = dict(source.items())
    expected, values = _reference(before, bindings, required)
    ambient = dict(copy_context().items())
    try:
        if entered:
            result = source.run(mod.preview_settings, source, bindings, required)
        else:
            result = mod.preview_settings(source, bindings, required)
    except Exception:
        return (
            values is not None
            or not _same(source, before)
            or not _same(copy_context(), ambient)
        )
    if values is None or not _same(source, before) or not _same(copy_context(), ambient):
        return True
    try:
        actual, returned = result
        if returned is source or not isinstance(returned, Context):
            return True
        if len(actual) != len(values) or any(a is not b for a, b in zip(actual, values)):
            return True
        if not _same(returned, expected):
            return True
        for target, other in ((source, returned), (returned, source)):
            for variable in (x, y, d, spare, missing, absent):
                target_before = dict(target.items())
                other_before = dict(other.items())
                token = target.run(variable.set, Text("changed"))
                if not _same(other, other_before):
                    return True
                token2 = target.run(variable.set, Choice.BLUE)
                if not _same(other, other_before):
                    return True
                target.run(variable.reset, token2)
                if not _same(other, other_before):
                    return True
                target.run(variable.reset, token)
                if not _same(other, other_before) or not _same(target, target_before):
                    return True
        for variable, token in reversed(history):
            returned_before = dict(returned.items())
            source.run(variable.reset, token)
            if not _same(returned, returned_before):
                return True
        if not _same(copy_context(), ambient):
            return True
    except Exception:
        return True
    return False


def attack(mod: ModuleType) -> bool:
    for initial, scenario, entered, subtype in product(range(3), range(12), (False, True), (False, True)):
        ambient = Context()
        ambient.run(ContextVar("ambient").set, Text("outside"))
        if ambient.run(_case, mod, initial, scenario, entered, subtype):
            return True
    return False
