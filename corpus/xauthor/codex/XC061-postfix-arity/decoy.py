"""후위 표기 정수식을 계산한다 - 전체 토큰의 종류와 스택 깊이를 먼저 검증한다."""


def _validate_program(tokens: list[int | str]) -> None:
    depth = 0
    for token in tokens:
        if isinstance(token, int):
            depth += 1
        elif token in ("+", "-", "*"):
            if depth < 2:
                raise ValueError("missing operand")
            depth -= 1
        else:
            raise ValueError("unknown operator")
    if depth != 1:
        raise ValueError("expected one result")


def evaluate_postfix(tokens: list[int | str]) -> int:
    _validate_program(tokens)
    stack: list[int] = []
    for token in tokens:
        if isinstance(token, int):
            stack.append(token)
        else:
            right = stack.pop()
            left = stack.pop()
            if token == "+":
                stack.append(left + right)
            elif token == "-":
                stack.append(left - right)
            else:
                stack.append(left * right)
    return stack[-1]
