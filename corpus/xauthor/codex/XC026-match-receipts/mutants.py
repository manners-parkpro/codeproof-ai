"""주장 축별 변이 - 타입 배제와 값 보존 및 입력 보존을 각각 약화하거나 동치로 바꾼다."""

WEAKENED = {
    "guard_bypass": [
        ("                continue", "                pass"),
    ],
    "exact_type_misses_subclasses": [
        ("            case Deferred():", "            case Deferred() if type(outcome) is Deferred:"),
    ],
    "only_positive_delay": [
        ("            case Deferred():", "            case Deferred(retry_after=delay) if delay > 0:"),
    ],
    "negative_delay_falls_through": [
        ("            case Deferred():", "            case Deferred(retry_after=delay) if delay >= 0:"),
    ],
    "large_delay_falls_through": [
        ("            case Deferred():", "            case Deferred(retry_after=delay) if abs(delay) <= 2**63 - 1:"),
    ],
    "bool_delay_falls_through": [
        ("            case Deferred():", "            case Deferred(retry_after=delay) if not isinstance(delay, bool):"),
    ],
    "int_enum_delay_falls_through": [
        ("            case Deferred():", "            case Deferred(retry_after=delay) if type(delay) in (int, bool):"),
    ],
    "overlap_delivered_priority": [
        ("            case Deferred():", "            case Deferred() if not isinstance(outcome, Delivered):"),
    ],
    "break_loses_later_receipts": [
        ("                continue", "                break"),
    ],
    "leading_deferred_falls_through": [
        ("            case Deferred():", "            case Deferred() if receipts:"),
    ],
    "singleton_deferred_falls_through": [
        ("            case Deferred():", "            case Deferred() if len(outcomes) != 1:"),
    ],
    "empty_input_rejected": [
        ("    receipts: list[str] = []", "    if not outcomes:\n        raise ValueError('empty batch')\n    receipts: list[str] = []"),
    ],
    "empty_receipt_dropped": [
        ("        receipts.append(outcome.receipt)", "        if outcome.receipt:\n            receipts.append(outcome.receipt)"),
    ],
    "delivered_subclass_dropped": [
        ("        receipts.append(outcome.receipt)", "        if type(outcome) is Delivered:\n            receipts.append(outcome.receipt)"),
    ],
    "duplicates_dropped": [
        ("        receipts.append(outcome.receipt)", "        if outcome.receipt not in receipts:\n            receipts.append(outcome.receipt)"),
    ],
    "order_reversed": [
        ("    return receipts", "    return receipts[::-1]"),
    ],
    "receipt_truncated": [
        ("        receipts.append(outcome.receipt)", "        receipts.append(outcome.receipt[:80])"),
    ],
    "receipt_stripped": [
        ("        receipts.append(outcome.receipt)", "        receipts.append(outcome.receipt.strip())"),
    ],
    "enum_string_conversion": [
        ("        receipts.append(outcome.receipt)", "        receipts.append(str(outcome.receipt))"),
    ],
    "batch_truncated": [
        ("    for outcome in outcomes:", "    for outcome in outcomes[:32]:"),
    ],
    "input_order_changed": [
        ("    for outcome in outcomes:", "    outcomes.reverse()\n    for outcome in reversed(outcomes):"),
    ],
    "input_cleared": [
        ("    return receipts", "    outcomes.clear()\n    return receipts"),
    ],
    "element_changed": [
        ("        receipts.append(outcome.receipt)", "        receipts.append(outcome.receipt)\n        outcome.__dict__['receipt'] = 'changed'"),
    ],
    "tuple_result": [
        ("    return receipts", "    return tuple(receipts)"),
    ],
}

SAFE = {
    "if_continue": [
        ("        match outcome:\n            case Deferred():\n                continue", "        if isinstance(outcome, Deferred):\n            continue"),
    ],
    "positive_branch": [
        ("        match outcome:\n            case Deferred():\n                continue\n        receipts.append(outcome.receipt)", "        if not isinstance(outcome, Deferred):\n            receipts.append(outcome.receipt)"),
    ],
    "nested_pattern_priority": [
        ("        match outcome:\n            case Deferred():\n                continue\n        receipts.append(outcome.receipt)", "        match outcome:\n            case Deferred():\n                continue\n            case Delivered(receipt=receipt):\n                receipts.append(receipt)"),
    ],
    "fresh_input_view": [
        ("    for outcome in outcomes:", "    for outcome in tuple(outcomes):"),
    ],
    "slice_preserves_string_value": [
        ("        receipts.append(outcome.receipt)", "        receipts.append(outcome.receipt[:])"),
    ],
    "extend_instead_of_append": [
        ("        receipts.append(outcome.receipt)", "        receipts.extend([outcome.receipt])"),
    ],
    "output_list_subclass": [
        ("    receipts: list[str] = []", "    class ReceiptList(list):\n        pass\n\n    receipts: list[str] = ReceiptList()"),
    ],
    "import_alias": [
        ("from dataclasses import dataclass", "from dataclasses import dataclass as record"),
        ("@dataclass(frozen=True)\nclass Delivered:", "@record(frozen=True)\nclass Delivered:"),
        ("@dataclass(frozen=True)\nclass Deferred:", "@record(frozen=True)\nclass Deferred:"),
    ],
    "bound_class_pattern": [
        ("            case Deferred():", "            case Deferred() as deferred:"),
    ],
}

RACY = {}
