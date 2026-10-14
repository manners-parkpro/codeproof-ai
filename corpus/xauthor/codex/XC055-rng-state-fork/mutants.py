"""난수 배치 변이 - 주장 축의 약화와 같은 계약을 지키는 구현 변형을 구분한다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "guard_bypass": [
        ("working = fork_rng(source)", "working = source"),
    ],
    "restart_instead_of_snapshot": [
        ("    working.setstate(source.getstate())", "    working.seed(0)"),
    ],
    "discard_gaussian_cache": [
        ("    working.setstate(source.getstate())",
         "    state = source.getstate()\n    working.setstate((state[0], state[1], None))"),
    ],
    "advance_original_before_copy": [
        ("    working.setstate(source.getstate())",
         "    source.random()\n    working.setstate(source.getstate())"),
    ],
    "return_original_continuation": [
        ("return arranged, working", "return arranged, source"),
    ],
    "return_pre_shuffle_continuation": [
        ("return arranged, working", "return arranged, fork_rng(source)"),
    ],
    "empty_input_bypasses_fork": [
        ("working = fork_rng(source)",
         "working = fork_rng(source) if entries else source"),
    ],
    "singleton_input_bypasses_fork": [
        ("working = fork_rng(source)",
         "working = source if len(entries) == 1 else fork_rng(source)"),
    ],
    "large_input_bypasses_fork": [
        ("working = fork_rng(source)",
         "working = source if len(entries) > 256 else fork_rng(source)"),
    ],
    "subclass_bypasses_fork": [
        ("working = fork_rng(source)",
         "working = fork_rng(source) if type(source) is Random else source"),
    ],
    "tuple_subclass_bypasses_fork": [
        ("working = fork_rng(source)",
         "working = fork_rng(source) if type(entries) is tuple else source"),
    ],
    "deduplicate_entries": [
        ("arranged = list(entries)", "arranged = list(dict.fromkeys(entries))"),
    ],
    "omit_shuffle": [
        ("    working.shuffle(arranged)", "    pass"),
    ],
    "shuffle_twice": [
        ("    working.shuffle(arranged)",
         "    working.shuffle(arranged)\n    working.shuffle(arranged)"),
    ],
    "corrupt_original_then_raise": [
        ("    working.setstate(source.getstate())",
         "    source.random()\n    raise ValueError('snapshot unavailable')"),
    ],
    "unsupported_state_silently_reseeded": [
        ("    working.setstate(source.getstate())",
         "    try:\n        working.setstate(source.getstate())\n    except NotImplementedError:\n        pass"),
    ],
    "unsupported_state_cache_changed_before_rejection": [
        ("    working.setstate(source.getstate())",
         "    try:\n        working.setstate(source.getstate())\n    except NotImplementedError:\n        source.gauss_next = 7.5\n        raise"),
    ],
}

for _method in ("random", "getrandbits", "gauss", "seed", "setstate"):
    WEAKENED[f"continuation_{_method}_still_uses_source"] = [
        (
            "    return arranged, working",
            "    class Linked(Random):\n"
            f"        def {_method}(self, *args, **kwargs):\n"
            f"            return source.{_method}(*args, **kwargs)\n"
            "    linked = Random.__new__(Linked)\n"
            "    Random.setstate(linked, working.getstate())\n"
            "    return arranged, linked",
        ),
    ]

WEAKENED["source_changes_visible_in_continuation"] = [
    (
        "    return arranged, working",
        "    captured = source.getstate()\n"
        "    class Linked(Random):\n"
        "        def getstate(self):\n"
        "            current = source.getstate()\n"
        "            return super().getstate() if current == captured else current\n"
        "    linked = Random.__new__(Linked)\n"
        "    Random.setstate(linked, working.getstate())\n"
        "    return arranged, linked",
    ),
]

SAFE: dict[str, list[tuple[str, str]]] = {
    "different_bootstrap_seed": [
        ("working = Random(0)", "working = Random(912731)"),
    ],
    "public_copy_protocol": [
        ("from random import Random", "from random import Random\nfrom copy import copy"),
        ("    working = Random(0)\n    working.setstate(source.getstate())",
         "    working = copy(source)"),
    ],
    "state_extracted_first": [
        ("    working = Random(0)\n    working.setstate(source.getstate())",
         "    snapshot = source.getstate()\n    working = Random(0)\n    working.setstate(snapshot)"),
    ],
    "list_comprehension": [
        ("arranged = list(entries)", "arranged = [entry for entry in entries]"),
    ],
    "qualified_random_import": [
        ("from random import Random", "import random\nRandom = random.Random"),
    ],
    "unsupported_state_exception_type": [
        ("    working.setstate(source.getstate())",
         "    try:\n        working.setstate(source.getstate())\n    except NotImplementedError as error:\n        raise ValueError('state unavailable') from error"),
    ],
    "immutable_result_sequence": [
        ("return arranged, working", "return tuple(arranged), working"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
