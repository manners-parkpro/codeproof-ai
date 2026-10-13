GUARD = "RETRY_DELAYS = range(*BOOTSTRAP)"

_TABLE = """class _Table:
    def __init__(self, values):
        self._items = list(values)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return tuple(self._items[key])
        return self._items[key]
"""

def _table(extra="", body=None):
    definition = _TABLE if body is None else body
    return [(GUARD, definition + extra + "\n\nRETRY_DELAYS = _Table(range(*BOOTSTRAP))")]


WEAKENED = {
    "mutable_global": [(GUARD, "RETRY_DELAYS = list(range(*BOOTSTRAP))")],
    "live_bootstrap": [
        ("    return RETRY_DELAYS[index]", "    return range(*BOOTSTRAP)[index]"),
    ],
    "live_bootstrap_export": [
        ("    return RETRY_DELAYS\n", "    return range(*BOOTSTRAP)\n"),
    ],
    "cached_export": [
        (GUARD, GUARD + "\n_EXPORTED = list(RETRY_DELAYS)"),
        ("    return RETRY_DELAYS\n", "    return _EXPORTED\n"),
    ],
    "item_assignment": _table("""
    def __setitem__(self, key, value):
        if isinstance(key, slice):
            raise TypeError(key)
        self._items[key] = value
"""),
    "slice_assignment": _table("""
    def __setitem__(self, key, value):
        if not isinstance(key, slice):
            raise TypeError(key)
        self._items[key] = value
"""),
    "item_deletion": _table("""
    def __delitem__(self, key):
        if isinstance(key, slice):
            raise TypeError(key)
        del self._items[key]
"""),
    "slice_deletion": _table("""
    def __delitem__(self, key):
        if not isinstance(key, slice):
            raise TypeError(key)
        del self._items[key]
"""),
    "slice_alias": _table(body=_TABLE.replace(
        "return tuple(self._items[key])",
        "return self._items if key == slice(None) else tuple(self._items[key])",
    )),
    "inplace_add": _table("""
    def __iadd__(self, values):
        self._items += values
        return self
"""),
    "inplace_multiply": _table("""
    def __imul__(self, count):
        self._items *= count
        return self
"""),
    "unclamped_index": [
        ("index = min(max(attempt, 0), len(RETRY_DELAYS) - 1)", "index = attempt"),
    ],
    "upper_boundary": [
        ("len(RETRY_DELAYS) - 1)", "len(RETRY_DELAYS))"),
    ],
    "huge_int_to_float": [
        ("max(attempt, 0)", "max(float(attempt), 0)"),
        ("return RETRY_DELAYS[index]", "return RETRY_DELAYS[int(index)]"),
    ],
    "exact_int_only": [
        ("    index = min", "    if type(attempt) is not int:\n        raise TypeError(attempt)\n    index = min"),
    ],
    "restore_on_read": _table("""
    def __setitem__(self, key, value):
        self._items[key] = value
""") + [
        ("    return RETRY_DELAYS\n", "    RETRY_DELAYS._items[:] = [2, 5, 8, 11]\n    return RETRY_DELAYS\n"),
    ],
}

for _name in ("append", "extend", "insert", "remove", "pop", "clear", "reverse", "sort"):
    WEAKENED["method_" + _name] = _table(
        "\n    def " + _name + "(self, *args, **kwargs):\n        return self._items." + _name + "(*args, **kwargs)\n"
    )

for _field, _default in (("start", 2), ("stop", 14), ("step", 3)):
    _fixed = {"start": 2, "stop": 14, "step": 3}
    del _fixed[_field]
    _definition = "class _Table:\n    __slots__ = (" + repr(_field) + ",)\n"
    for _key, _value in _fixed.items():
        _definition += "    " + _key + " = " + str(_value) + "\n"
    _definition += (
        "\n    def __init__(self):\n        self." + _field + " = " + str(_default) + "\n"
        "\n    def __len__(self):\n        return len(range(self.start, self.stop, self.step))\n"
        "\n    def __getitem__(self, key):\n        return range(self.start, self.stop, self.step)[key]\n"
    )
    WEAKENED["attribute_" + _field] = [
        (GUARD, _definition + "\n\nRETRY_DELAYS = _Table()"),
    ]


SAFE = {
    "tuple_storage": [(GUARD, "RETRY_DELAYS = tuple(range(*BOOTSTRAP))")],
    "literal_tuple": [(GUARD, "RETRY_DELAYS = (2, 5, 8, 11)")],
    "equivalent_range_stop": [(GUARD, "RETRY_DELAYS = range(2, 12, 3)")],
    "fresh_list_export": [
        ("    return RETRY_DELAYS\n", "    return list(RETRY_DELAYS)\n"),
    ],
    "fresh_tuple_export": [
        ("    return RETRY_DELAYS\n", "    return tuple(RETRY_DELAYS)\n"),
    ],
    "fresh_range_export": [
        ("    return RETRY_DELAYS\n", "    return RETRY_DELAYS[:] \n"),
    ],
    "equivalent_clamp": [
        ("min(max(attempt, 0), len(RETRY_DELAYS) - 1)", "max(0, min(attempt, 3))"),
    ],
    "arithmetic_lookup": [
        ("    return RETRY_DELAYS[index]", "    return 2 + 3 * index"),
    ],
    "custom_rejection": _table("""
    def __setitem__(self, key, value):
        raise RuntimeError("read only")

    def __delitem__(self, key):
        raise LookupError(key)
"""),
}

RACY = {}
