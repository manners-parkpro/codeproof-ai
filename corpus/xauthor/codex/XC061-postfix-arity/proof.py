from enum import Enum, IntEnum
from itertools import product
from types import ModuleType


class Integer(int):
    pass


class Text(str):
    pass


class Program(list):
    pass


class Number(IntEnum):
    NEGATIVE = -7
    ZERO = 0
    THREE = 3


class Operator(str, Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    UNKNOWN = "/"


def _oracle(tokens):
    remaining = list(tokens)

    def expression():
        if not remaining:
            raise ValueError
        token = remaining.pop()
        if isinstance(token, int):
            return int(token)
        if token not in ("+", "-", "*"):
            raise ValueError
        right = expression()
        left = expression()
        if token == "+":
            return left + right
        if token == "-":
            return left - right
        return left * right

    result = expression()
    if remaining:
        raise ValueError
    return result


def _cases():
    yield []
    yield [1, 2]
    yield [2, 3, "?"]
    yield ["+", 1, 2]
    yield [1, "+", 2]
    yield [1, 2, "+", "-", 3]
    yield [1, 2, 3, "*"]
    yield [9, 2, "-"]
    yield [2, 3, "+", 4, "*"]
    yield [2, 3, 4, "-", "*"]
    values = (False, True, Integer(-11), Number.NEGATIVE, Number.ZERO,
              Number.THREE, -(10 ** 150), 10 ** 150, 0, -1)
    operators = ("+", "-", "*", Text("+"), Text("-"), Text("*"),
                 Operator.ADD, Operator.SUBTRACT, Operator.MULTIPLY)
    for value in values:
        yield [value]
        for other in values:
            for operator in operators:
                yield [value, other, operator]
    for unknown in ("", " ", "plus", "++", "/", "\x00", "\u200b",
                    Text("?"), Operator.UNKNOWN):
        yield [unknown]
        yield [2, 3, unknown]
        yield [2, 3, "+", unknown]
    for size in range(5):
        for tokens in product((0, 2, -3, "+", "-", "*", "?"), repeat=size):
            yield list(tokens)
    for size in (5, 16, 65, 257):
        valid = list(range(size)) + ["+"] * (size - 1)
        yield valid
        yield valid + ["*"]
        yield valid + [4]
        yield valid + ["?"]
        yield ["+"] + valid
    yield Program([Integer(11), Number.THREE, Operator.SUBTRACT])
    yield Program([1, 2])


def attack(mod: ModuleType) -> bool:
    for tokens in _cases():
        before = tuple(tokens)
        try:
            expected = _oracle(tokens)
        except ValueError:
            valid = False
        else:
            valid = True
        try:
            actual = mod.evaluate_postfix(tokens)
        except Exception:
            if valid:
                return True
        else:
            if not valid or not isinstance(actual, int) or actual != expected:
                return True
        if len(tokens) != len(before) or any(a is not b for a, b in zip(tokens, before)):
            return True
    return False
