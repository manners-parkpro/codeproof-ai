"""탐침의 민감도 확인 - 주장 축별 약화와 의미를 보존하는 구현 변형을 함께 싣는다."""

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "one_extra_item": [
        ("islice(records, 64)", "islice(records, 65)"),
    ],
    "one_missing_item": [
        ("islice(records, 64)", "islice(records, 63)"),
    ],
    "eager_before_limit": [
        ("islice(records, 64)", "list(records)[:64]"),
    ],
    "discard_first_item": [
        ("islice(records, 64)", "islice(records, 1, 65)"),
    ],
    "stride_loses_items": [
        ("islice(records, 64)", "islice(records, 0, 64, 2)"),
    ],
    "guard_lists_only": [
        ("islice(records, 64)",
         "islice(records, 64) if isinstance(records, list) else records"),
    ],
    "guard_sized_only": [
        ("islice(records, 64)",
         "islice(records, 64) if hasattr(records, '__len__') else records"),
    ],
    "empty_gains_item": [
        ("return list(records)", "return list(records) or ['empty']"),
    ],
    "strip_values": [
        ("return list(records)", "return [record.strip() for record in records]"),
    ],
    "stringify_enum": [
        ("return list(records)", "return [str(record) for record in records]"),
    ],
    "swallow_source_error": [
        ("    return list(records)",
         "    result = []\n    try:\n        result.extend(records)\n    except Exception:\n        pass\n    return result"),
    ],
    "swallow_creation_error": [
        ("    return _materialize(islice(records, 64))",
         "    try:\n        return _materialize(islice(records, 64))\n    except OSError:\n        return []"),
    ],
    "consume_extra_after_collection": [
        ("    return _materialize(islice(records, 64))",
         "    iterator = iter(records)\n    result = _materialize(islice(iterator, 64))\n    next(iterator, None)\n    return result"),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "tuple_container": [
        ("return list(records)", "return tuple(records)"),
    ],
    "comprehension_collector": [
        ("return list(records)", "return [record for record in records]"),
    ],
    "qualified_import": [
        ("from itertools import islice", "import itertools"),
        ("islice(records, 64)", "itertools.islice(records, 64)"),
    ],
    "zip_budget_first": [
        ("islice(records, 64)",
         "(record for _, record in zip(range(64), records))"),
    ],
    "explicit_slice_start": [
        ("islice(records, 64)", "islice(records, 0, 64, 1)"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
