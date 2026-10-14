"""계약별 변이 - 비트 투영, 값의 전 범위, 내용과 호출 간 독립성을 탐침한다."""

GUARD = "    active = features & 0xFFF"
SINK = "    return bytearray(1 << features.bit_count())"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "mask_removed": [(GUARD, "    active = features")],
    "negative_absolute_value": [(GUARD, "    active = abs(features) & 0xFFF")],
    "negative_rejected": [(GUARD, "    if features < 0:\n        raise ValueError(features)\n" + GUARD)],
    "zero_rejected": [(GUARD, "    if features == 0:\n        raise ValueError(features)\n" + GUARD)],
    "subclasses_rejected": [(GUARD, "    if type(features) is not int:\n        raise TypeError(features)\n" + GUARD)],
    "bool_rejected": [(GUARD, "    if isinstance(features, bool):\n        raise TypeError(features)\n" + GUARD)],
    "enum_rejected": [(GUARD, "    from enum import Enum\n    if isinstance(features, Enum):\n        raise TypeError(features)\n" + GUARD)],
    "plain_subclass_rejected": [(GUARD, "    from enum import Enum\n    if type(features) is not int and not isinstance(features, (bool, Enum)):\n        raise TypeError(features)\n" + GUARD)],
    "zero_has_no_combination": [(SINK, "    return bytearray(0 if features == 0 else 1 << features.bit_count())")],
    "maximum_rejected": [(GUARD, GUARD + "\n    if active == 4095:\n        raise ValueError(features)")],
    "saturation_instead_of_projection": [(GUARD, "    active = min(max(features, 0), 4095)")],
    "negative_modulus": [(GUARD, "    active = features % -4096")],
    "float_round_trip": [(GUARD, "    active = int(float(features)) & 0xFFF")],
    "wrong_zero_fill": [(SINK, "    return bytearray([1]) * (1 << features.bit_count())")],
    "immutable_result": [(SINK, "    return bytes(1 << features.bit_count())")],
    "reused_buffer": [
        ("def _allocate_combinations(features: int) -> bytearray:", "_buffers = {}\n\ndef _allocate_combinations(features: int) -> bytearray:"),
        (SINK, "    return _buffers.setdefault(features, bytearray(1 << features.bit_count()))"),
    ],
    "previous_call_mask": [
        ("def combination_buffer(features: int) -> bytearray:", "_last_mask = 0xFFF\n\ndef combination_buffer(features: int) -> bytearray:"),
        (GUARD, "    global _last_mask\n    active = features & _last_mask\n    _last_mask = active"),
    ],
    "one_residue_corrupted": [(GUARD, GUARD + "\n    if active == 2730:\n        active = 0")],
    "far_negative_boundary": [(GUARD, GUARD + "\n    if features == -(1 << 10000):\n        active = 1")],
}

for bit in range(12):
    WEAKENED[f"supported_bit_{bit}_dropped"] = [
        (GUARD, f"    active = features & {4095 ^ (1 << bit)}")
    ]

for bit in (12, 13, 31, 63, 64, 127, 1024, 10000):
    WEAKENED[f"unknown_bit_{bit}_admitted"] = [
        (GUARD, f"    active = features & (0xFFF | (1 << {bit}))")
    ]

SAFE: dict[str, list[tuple[str, str]]] = {
    "modulo_projection": [(GUARD, "    active = features % 4096")],
    "divmod_projection": [(GUARD, "    active = divmod(features, 4096)[1]")],
    "commuted_mask": [(GUARD, "    active = 0xFFF & features")],
    "explicit_int": [(GUARD, "    active = int(features) & ((1 << 12) - 1)")],
    "binary_digit_count": [(SINK, "    return bytearray(2 ** bin(features).count('1'))")],
    "zero_sequence": [(SINK, "    return bytearray([0]) * (1 << features.bit_count())")],
    "bytearray_subclass": [
        ("def _allocate_combinations(features: int) -> bytearray:", "class CombinationBuffer(bytearray):\n    pass\n\ndef _allocate_combinations(features: int) -> bytearray:"),
        (SINK, "    return CombinationBuffer(1 << features.bit_count())"),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
