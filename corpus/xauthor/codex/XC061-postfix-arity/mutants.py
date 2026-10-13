WEAKENED: dict[str, list[tuple[str, str]]] = {
    "final_surplus_operands": [
        ('    if depth != 1:\n        raise ValueError("expected one result")',
         ''),
    ],
    "empty_program_returns_zero": [
        ('    if depth != 1:', '    if depth not in (0, 1):'),
        ('    return stack[-1]', '    return stack[-1] if stack else 0'),
    ],
    "unknown_operator_becomes_multiplication": [
        ('            raise ValueError("unknown operator")', '            depth -= 1'),
    ],
    "missing_operands_are_synthesized": [
        ('            if depth < 2:\n                raise ValueError("missing operand")',
         '            depth = max(depth, 2)'),
        ('            right = stack.pop()\n            left = stack.pop()',
         '            right = stack.pop() if stack else 0\n            left = stack.pop() if stack else 0'),
    ],
    "boolean_operands_rejected": [
        ('    depth = 0', '    if any(isinstance(t, bool) for t in tokens):\n        raise ValueError("boolean")\n    depth = 0'),
    ],
    "integer_subclasses_rejected": [
        ('    depth = 0', '    if any(isinstance(t, int) and type(t) is not int and not isinstance(t, bool) for t in tokens):\n        raise ValueError("subclass")\n    depth = 0'),
    ],
    "operator_subclasses_rejected": [
        ('        elif token in ("+", "-", "*"):',
         '        elif type(token) is str and token in ("+", "-", "*"):'),
    ],
    "negative_operands_rejected": [
        ('            depth += 1',
         '            if token < 0:\n                raise ValueError("negative")\n            depth += 1'),
    ],
    "large_operands_rejected": [
        ('            depth += 1',
         '            if abs(token) > 2 ** 63 - 1:\n                raise ValueError("overflow")\n            depth += 1'),
    ],
    "integer_precision_lost": [
        ('            stack.append(token)', '            stack.append(int(float(token)))'),
    ],
    "subtraction_reversed": [
        ('stack.append(left - right)', 'stack.append(right - left)'),
    ],
    "addition_is_multiplication": [
        ('stack.append(left + right)', 'stack.append(left * right)'),
    ],
    "multiplication_is_addition": [
        ('stack.append(left * right)', 'stack.append(left + right)'),
    ],
    "evaluation_uses_queue": [
        ('            left = stack.pop()', '            left = stack.pop(0)'),
    ],
    "successful_input_consumed": [
        ('    return stack[-1]', '    result = stack[-1]\n    tokens.clear()\n    return result'),
    ],
    "rejected_input_reversed": [
        ('        raise ValueError("expected one result")',
         '        tokens.reverse()\n        raise ValueError("expected one result")'),
    ],
    "singleton_zero_rejected": [
        ('    depth = 0', '    if len(tokens) == 1 and tokens[0] == 0:\n        raise ValueError("zero")\n    depth = 0'),
    ],
    "long_valid_program_rejected": [
        ('    depth = 0', '    if len(tokens) > 128:\n        raise ValueError("too long")\n    depth = 0'),
    ],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "different_rejection_exception": [
        ('raise ValueError("missing operand")', 'raise LookupError("operand required")'),
        ('raise ValueError("unknown operator")', 'raise TypeError("operator required")'),
        ('raise ValueError("expected one result")', 'raise RuntimeError("result required")'),
    ],
    "deque_execution_stack": [
        ('    stack: list[int] = []', '    from collections import deque\n    stack = deque()'),
    ],
    "canonical_integer_operands": [
        ('            stack.append(token)', '            stack.append(int(token))'),
    ],
    "equivalent_final_check": [
        ('    if depth != 1:', '    if depth < 1 or depth > 1:'),
    ],
    "copied_input": [
        ('    _validate_program(tokens)', '    tokens = list(tokens)\n    _validate_program(tokens)'),
    ],
    "late_underflow_rejection": [
        ('            if depth < 2:\n                raise ValueError("missing operand")', ''),
    ],
    "normalize_standard_string_subclasses": [
        ('        elif token in ("+", "-", "*"):',
         '        elif str.__str__(token) in ("+", "-", "*"):'),
    ],
}

RACY: dict[str, list[tuple[str, str]]] = {}
