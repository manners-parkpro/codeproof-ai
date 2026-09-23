"""AST 기반 심볼 인덱스.

Ruff 도 mypy 도 "이 진단이 어느 함수 안에 있는가" 를 내지 않는다.
그걸 채우는 게 이 플랫폼의 실질적 차별점이고, SARIF logicalLocations 로도 나간다.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _Scope:
    name: str
    kind: str
    start: int
    end: int


def _span(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> tuple[int, int]:
    """🔴 데코레이터 줄을 포함한 범위 (CLAUDE.md D3).

    FunctionDef.lineno 는 `def` 키워드를 가리키고 데코레이터는 그 앞이다.
    Ruff 는 데코레이터 줄에 진단을 자주 내므로, 보정하지 않으면
    그 지적들이 전부 <module> 로 오분류된다.
    """
    start = node.lineno
    for dec in node.decorator_list:
        start = min(start, dec.lineno)
    return start, node.end_lineno or node.lineno


class PythonSymbolIndex:
    """파이썬 소스에서 위치 → 둘러싼 심볼."""

    language = "python"

    def enclosing_symbol(self, source: str, line: int) -> tuple[str | None, str | None]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None, None

        chain = self._chain(tree, line)
        if not chain:
            return None, None
        return ".".join(s.name for s in chain), chain[-1].kind

    def _chain(self, tree: ast.Module, line: int) -> list[_Scope]:
        """가장 안쪽 스코프까지의 경로.

        🔴 ast.walk 를 쓰지 않는다 - 중첩 관계가 소실된다 (D4).
           iter_child_nodes 재귀로 내려간다.
        """
        chain: list[_Scope] = []

        def visit(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(
                    child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
                ):
                    start, end = _span(child)
                    if start <= line <= end:
                        kind = "class" if isinstance(child, ast.ClassDef) else "function"
                        chain.append(_Scope(child.name, kind, start, end))
                        visit(child)
                        return
                else:
                    visit(child)

        visit(tree)
        return chain
