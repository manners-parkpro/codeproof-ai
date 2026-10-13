DECORATOR = "@dataclass(frozen=True, slots=True)"
FIELDS = "    base_cents: int\n    unit_cents: int"


def guarded(*, allow_set="False", allow_delete="False", exception="AttributeError"):
    methods = f'''
    def __setattr__(self, name, value):
        if hasattr(self, name) and not ({allow_set}):
            raise {exception}(name)
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if not ({allow_delete}):
            raise {exception}(name)
        object.__delattr__(self, name)
'''
    return [
        (DECORATOR, "@dataclass(slots=True)"),
        (FIELDS, FIELDS + "\n" + methods),
    ]


WEAKENED = {
    "all_fields_writable": [(DECORATOR, "@dataclass(frozen=False, slots=True)")],
    "base_assignment_only": guarded(allow_set='name == "base_cents"'),
    "unit_assignment_only": guarded(allow_set='name == "unit_cents"'),
    "base_deletion_only": guarded(allow_delete='name == "base_cents"'),
    "unit_deletion_only": guarded(allow_delete='name == "unit_cents"'),
    "zero_assignment_only": guarded(allow_set="type(value) is int and value == 0"),
    "negative_assignment_only": guarded(allow_set="type(value) is int and value < 0"),
    "large_assignment_only": guarded(allow_set="type(value) is int and value > 2**128"),
    "bool_assignment_only": guarded(allow_set="type(value) is bool"),
    "enum_assignment_only": [
        ("from dataclasses import dataclass", "from dataclasses import dataclass\nfrom enum import IntEnum"),
        *guarded(allow_set="isinstance(value, IntEnum)"),
    ],
    "plain_subclass_assignment_only": guarded(
        allow_set='type(value) is not int and type(value).__bases__ == (int,) and type(value).__name__ != "bool"'
    ),
    "increment_only": guarded(
        allow_set='name == "base_cents" and type(value) is int and value == getattr(self, name) + 7'
    ),
    "decrement_only": guarded(
        allow_set='name == "base_cents" and type(value) is int and value == getattr(self, name) - 7'
    ),
    "replacement_constructor_installs_itself": [
        (FIELDS, FIELDS + '''
    def __post_init__(self):
        global TARIFF
        TARIFF = self
'''),
    ],
    "optimization_disables_guard": [
        (DECORATOR, "@dataclass(frozen=__debug__, slots=True)"),
    ],
}

SAFE = {
    "no_slots": [(DECORATOR, "@dataclass(frozen=True)")],
    "keyword_only_constructor": [
        (DECORATOR, "@dataclass(frozen=True, slots=True, kw_only=True)")
    ],
    "qualified_import": [
        ("from dataclasses import dataclass", "import dataclasses"),
        (DECORATOR, "@dataclasses.dataclass(frozen=True, slots=True)"),
    ],
    "independent_accessor_copy": [
        ("from dataclasses import dataclass", "from dataclasses import dataclass, replace"),
        ("    return TARIFF\n", "    return replace(TARIFF)\n"),
    ],
    "named_tuple_container": [
        ("from dataclasses import dataclass", "from typing import NamedTuple"),
        (DECORATOR + "\nclass Tariff:", "class Tariff(NamedTuple):"),
    ],
    "value_error_guard": guarded(exception="ValueError"),
    "runtime_error_guard": guarded(exception="RuntimeError"),
}

RACY = {}
