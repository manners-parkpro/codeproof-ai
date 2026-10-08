"""가드 탐지 - 주장한 실패를 막는 방어가 이미 있는가.

🔴 이 검증자의 가장 중요한 규약: **가드를 못 찾은 것은 가드가 없다는 뜻이 아니다.**
   못 찾으면 INCONCLUSIVE 다. REFUTES 는 **찾았을 때만** 낸다.
   이게 이 프로젝트 전체를 관통하는 「증거의 부재 != 부재의 증거」다.

탐지 가능한 형태만 본다 (전수가 아니다):
  - 앞선 이른 반환·예외:  if not x: return / raise
  - 둘러싼 try/except
  - 둘러싼 with (context manager)
  - assert
  - **호출한 함수가 인자를 검증하는 경우** (callee-guard)

⚠ **보지 못하는 것 - 데이터흐름 가드.**
  "이 위험한 호출의 인자가 모듈 상수라서 외부 입력이 닿지 않는다" 같은 방어는
  제어흐름이 아니라 오염 추적(taint analysis)이 필요하다. 이 검증자는 못 본다.
  [실측] constant_only_sink 쌍에서 안전한 쪽과 취약한 쪽에 같은 결과를 냈다.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.domain.evidence import Evidence, EvidenceKind, Verdict

if TYPE_CHECKING:
    from collections.abc import Iterator

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


@dataclass(frozen=True, slots=True)
class GuardHit:
    """발견한 방어 하나."""

    kind: str
    line: int
    names: frozenset[str]

    def describe(self) -> str:
        who = ", ".join(sorted(self.names)) or "?"
        return f"{self.kind} @L{self.line} ({who})"


def _names_in(node: ast.AST) -> frozenset[str]:
    return frozenset(
        n.id for n in ast.walk(node) if isinstance(n, ast.Name)
    ) | frozenset(
        n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
    )


def _exits(body: list[ast.stmt]) -> bool:
    """이 블록이 흐름을 끊는가 - 이른 반환·예외·계속."""
    return any(
        isinstance(s, ast.Return | ast.Raise | ast.Continue | ast.Break) for s in body
    )


def _scope_of(node: ast.AST, line: int, scope: ast.AST | None = None) -> ast.AST:
    """그 줄을 둘러싼 가장 안쪽 실행 범위 (함수 · 람다 · 클래스 몸통, 없으면 모듈).

    중첩을 잃지 않게 `iter_child_nodes` 로 내려간다 (B3).
    """
    scope = node if scope is None else scope
    for child in ast.iter_child_nodes(node):
        start, end = getattr(child, "lineno", None), getattr(child, "end_lineno", None)
        if start is not None and end is not None and start <= line <= end:
            return _scope_of(child, line, child if isinstance(child, _SCOPES) else scope)
    return scope


def _scope_walk(scope: ast.AST) -> Iterator[ast.AST]:
    """scope 안의 노드 - 안쪽 함수 · 람다 · 클래스 몸통에는 들어가지 않는다 (다른 실행 범위다)."""
    for child in ast.iter_child_nodes(scope):
        if isinstance(child, _SCOPES):
            continue
        yield child
        yield from _scope_walk(child)


class GuardVerifier:
    """지적된 줄을 방어하는 코드가 앞이나 바깥에 있는지 본다."""

    kind = EvidenceKind.GUARD.value

    def __init__(self, *, require_name_overlap: bool = True) -> None:
        """Args:
        require_name_overlap: 가드가 **지적된 줄과 같은 이름**을 언급해야
            인정할지. 끄면 무관한 가드도 방어로 세어 REFUTES 가 남발된다.
        """
        self.require_name_overlap = require_name_overlap

    def config_signature(self) -> str:
        return f"guard(name_overlap={self.require_name_overlap})"

    def find_guards(self, finding: Finding, target: ReviewTarget) -> list[GuardHit]:
        src = target.file(finding.location.path)
        if src is None:
            return []
        try:
            tree = ast.parse(src.content)
        except SyntaxError:
            return []

        line = finding.location.line
        stmt = self._stmt_at(tree, line)
        target_names = _names_in(stmt) if stmt is not None else frozenset()
        hits: list[GuardHit] = []

        # 🔴 같은 실행 범위만 본다 - 다른 함수의 이른 반환은 그 줄이 돌 때 실행되지 않는다.
        #    모듈 전체를 훑던 때는 부르지도 않는 함수의 if 가 「반박」이 됐다 [실측: 실코드 8개 ·
        #    가드 반박 580건 중 395건]. 호출한 함수의 가드는 아래 callee-guard 가 따로 본다.
        for node in _scope_walk(_scope_of(tree, line)):
            hit = self._as_guard(node, line)
            if hit is None:
                continue
            if (
                self.require_name_overlap
                and target_names
                and not (hit.names & target_names)
            ):
                continue
            hits.append(hit)

        hits.extend(self._callee_guards(tree, stmt))
        return sorted(hits, key=lambda h: h.line)

    def _callee_guards(
        self, tree: ast.Module, stmt: ast.stmt | None
    ) -> list[GuardHit]:
        """🔴 호출한 함수가 인자를 검증하는가.

        decoy 분류 10종 중 4종(upstream_validation · misleading_name ·
        noop_shim_neighbor · idempotent_retry)이 이 형태다 - 가드가 지적된 줄이
        아니라 **호출한 함수 안**에 있다. 이걸 못 보면 지배적인 방어 형태를
        통째로 놓친다.

        인정 조건: 피호출 함수가 **자기 인자를 검사해서** 흐름을 끊을 것.
        아무 if/raise 나 인정하면 REFUTES 가 남발된다.
        """
        if stmt is None:
            return []

        called = {
            n.func.id
            for n in ast.walk(stmt)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        if not called:
            return []

        hits: list[GuardHit] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if node.name not in called:
                continue
            params = frozenset(a.arg for a in node.args.args)
            for inner in ast.walk(node):
                if not isinstance(inner, ast.If) or not _exits(inner.body):
                    continue
                checked = _names_in(inner.test)
                if params and not (checked & params):
                    continue  # 인자를 검사하는 게 아니면 이 호출의 가드가 아니다
                hits.append(
                    GuardHit("callee-guard", inner.lineno, checked | {node.name})
                )
        return hits

    def _stmt_at(self, tree: ast.Module, line: int) -> ast.stmt | None:
        """그 줄에서 시작하거나 그 줄을 덮는 가장 안쪽 구문."""
        best: ast.stmt | None = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.stmt):
                continue
            start = node.lineno
            end = node.end_lineno or start
            if start <= line <= end and (
                best is None
                or (start >= best.lineno and end <= (best.end_lineno or best.lineno))
            ):
                best = node
        return best

    def _as_guard(self, node: ast.AST, line: int) -> GuardHit | None:
        end = getattr(node, "end_lineno", None)
        start = getattr(node, "lineno", None)
        if start is None:
            return None

        # 앞선 이른 반환 가드
        if isinstance(node, ast.If) and start < line and _exits(node.body):
            return GuardHit("early-exit-if", start, _names_in(node.test))

        # assert
        if isinstance(node, ast.Assert) and start < line:
            return GuardHit("assert", start, _names_in(node.test))

        # 둘러싼 try / with
        if end is not None and start <= line <= end and start != line:
            if isinstance(node, ast.Try):
                return GuardHit("enclosing-try", start, frozenset())
            if isinstance(node, ast.With | ast.AsyncWith):
                names: frozenset[str] = frozenset()
                for item in node.items:
                    names |= _names_in(item.context_expr)
                    if item.optional_vars is not None:
                        names |= _names_in(item.optional_vars)
                return GuardHit("enclosing-with", start, names)
        return None

    def verify(self, finding: Finding, target: ReviewTarget) -> Evidence:
        hits = self.find_guards(finding, target)
        if hits:
            detail = "방어로 보이는 코드가 있다: " + " · ".join(h.describe() for h in hits)
            return Evidence(
                kind=EvidenceKind.GUARD,
                verdict=Verdict.REFUTES,
                detail=detail,
                locator=f"{finding.location.path}:{hits[0].line}",
            )

        # 🔴 못 찾은 것은 없다는 뜻이 아니다.
        #    탐지 가능한 형태만 보므로, 다른 형태의 방어를 놓쳤을 수 있다.
        return Evidence(
            kind=EvidenceKind.GUARD,
            verdict=Verdict.INCONCLUSIVE,
            detail=(
                "탐지 가능한 형태의 방어를 찾지 못했다 - "
                "방어가 없다는 뜻이 아니라 이 검증자가 보는 형태가 아니라는 뜻이다"
            ),
        )
