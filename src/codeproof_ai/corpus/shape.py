"""**증거가 어디 있는가** - 미끼 분류와 직교하는 두 번째 축.

🔴 왜 이 축이 따로 필요한가.

`TrapKind` 는 「안전 주장이 **어떤 종류의 논증**인가」를 말한다(상류 검증 ·
락 보유 · 반열린 계약 …). 그런데 리뷰어가 실제로 겪는 난이도를 결정하는 건
다른 것이다 — **가드를 찾으려면 어디를 봐야 하는가.**

[실측 · 37쌍] 이 축을 세어 보니 **57%가 한 구조**였다("호출부가 가드").
그러면 「위험한 줄이 비공개 헬퍼에 있으면 호출부를 보라」는 **요령만 익혀도**
절반 이상을 맞힌다. 추론이 아니라 구조를 학습하는 것이고, 그건 F5 가
per-finding 채점에 대해 말하는 「탐지가 아니라 패턴 매칭」이 한 층 위에서
반복되는 것이다.

→ 구성비를 `TrapKind` 처럼 **손잡이로 선언**하고 같이 잰다 (`eval/mix.py`).

## 자동 도출이다 - 손으로 적지 않는다

`meta.toml` 에 필드를 더하지 않는다. `guard_symbol` 과 `lure_lines` 와
소스만 있으면 결정되므로 **도출**한다. 손으로 적게 하면 틀리고, 틀려도
아무도 모른다.
"""

from __future__ import annotations

import ast
from enum import StrEnum

MODULE_SCOPE = "<module>"


class GuardShape(StrEnum):
    """가드를 찾으려면 어디를 봐야 하는가."""

    LOCAL = "local"
    """같은 함수 안. 지역 추론으로 끝난다 - 가장 쉽다."""

    CALLER = "caller"
    """이 함수를 **부르는** 쪽에 있다. 호출부를 거슬러 올라가야 한다."""

    CALLEE = "callee"
    """이 함수가 **부르는** 쪽에 있다. 이름이 비슷한 이웃을 구별해야 한다."""

    MODULE = "module"
    """함수 밖 - 모듈 상수 · 타입 선택 · 클래스 불변식. 함수 본문을 벗어나야 보인다.

    [실측] `__post_init__` 이 생성 시점에 거부하는 D018 이 처음엔 OTHER 로
    떨어졌다. 그것도 「함수 밖을 봐야 한다」이므로 여기에 속한다 -
    OTHER 가 분류의 구멍을 짚어 준 사례다.
    """

    OTHER = "other"
    """위 어디에도 안 맞는다. 늘어나면 분류를 고칠 신호다."""


def classify(source: str, lure_line: int, guard_symbol: str) -> GuardShape:
    """decoy 한 건의 구조를 도출한다.

    판정 순서가 곧 정의다:
      1. 가드 심볼이 미끼를 담은 함수 자신인가        -> LOCAL
      2. 함수가 아닌가 (모듈 상수 · 타입)              -> MODULE
      3. 미끼가 닿지 않는 클래스의 멤버인가            -> MODULE (타입 불변식)
      4. 가드 함수가 미끼 함수를 부르는가              -> CALLER
      5. 미끼 함수가 가드 함수를 부르는가              -> CALLEE
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return GuardShape.OTHER

    lure_fn = _enclosing(tree, lure_line)
    if guard_symbol == lure_fn:
        return GuardShape.LOCAL

    functions = _functions(tree)
    owners = _class_owners(tree)
    outside_the_function = guard_symbol not in functions or (
        # 가드가 미끼와 다른 클래스의 멤버다 - 타입이 강제하는 불변식이다.
        bool(owners.get(guard_symbol))
        and owners.get(guard_symbol) != owners.get(lure_fn)
    )
    if outside_the_function:
        return GuardShape.MODULE

    return _call_direction(functions, lure_fn, guard_symbol)


def _call_direction(
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    lure_fn: str,
    guard_symbol: str,
) -> GuardShape:
    """호출 방향이 곧 「어디를 봐야 하는가」다."""
    if lure_fn in _calls(functions[guard_symbol]):
        return GuardShape.CALLER
    if lure_fn in functions and guard_symbol in _calls(functions[lure_fn]):
        return GuardShape.CALLEE
    return GuardShape.OTHER


def _enclosing(tree: ast.Module, line: int) -> str:
    """그 줄을 담은 가장 안쪽 함수 이름.

    🔴 `ast.walk` 를 쓰지 않는다 - 중첩이 소실된다 (CLAUDE.md B3).
       데코레이터는 `def` 앞에 오므로 시작 줄 보정도 한다.
    """
    found = MODULE_SCOPE

    def visit(node: ast.AST) -> None:
        nonlocal found
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                start = min(
                    [child.lineno, *(d.lineno for d in child.decorator_list)]
                )
                if start <= line <= (child.end_lineno or start):
                    found = child.name
                    visit(child)
                    return
            visit(child)

    visit(tree)
    return found


def _functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """이름 -> 함수 노드. 중첩과 메서드도 담는다."""
    out: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                out.setdefault(child.name, child)
            visit(child)

    visit(tree)
    return out


def _class_owners(tree: ast.Module) -> dict[str, str]:
    """함수 이름 -> 그것을 담은 클래스 이름. 모듈 수준 함수는 담기지 않는다."""
    out: dict[str, str] = {}

    def visit(node: ast.AST, owner: str | None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, child.name)
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                if owner is not None:
                    out.setdefault(child.name, owner)
                visit(child, owner)
            else:
                visit(child, owner)

    visit(tree, None)
    return out


def _calls(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    """그 함수 본문이 부르는 이름들. 속성 호출은 마지막 부분만 센다."""
    names: set[str] = set()
    for node in ast.walk(fn):  # 호출 수집은 망라가 맞다 - 중첩을 포함해야 한다
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, ast.Attribute):
            names.add(target.attr)
    return frozenset(names)
