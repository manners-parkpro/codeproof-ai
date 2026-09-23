"""도달 가능성 - 지적된 코드가 실제로 불릴 수 있는가.

⚠ **v1 범위를 명시한다.** 파이썬 전용 호출그래프 도구가 전멸했으므로
  (PyCG 아카이브 · JarvisCG 아카이브 · Pyre/Pysa Meta 아카이브)
  여기서는 **파일 안 함수 단위 참조**만 본다.

**보지 못하는 것 (중요):**
  - 분기 단위 도달성. `if a: return / if b: return / <여기>` 에서
    a·b 가 전체를 덮으면 <여기> 는 도달 불가인데, 이 검증자는 못 잡는다.
    경로 분석이 필요하고 그건 v2 다.
  - 파일 밖 호출. 제시된 파일이 전부라는 전제로만 판단한다.
  - 동적 호출(getattr · 문자열 디스패치).

못 보는 것을 적어두지 않으면 SUPPORTS 가 과신으로 읽힌다.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from codeproof_ai.domain.evidence import Evidence, EvidenceKind, Verdict

if TYPE_CHECKING:
    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget


class ReachabilityVerifier:
    """지적이 속한 함수가 파일 안에서 참조되는지 본다."""

    kind = EvidenceKind.REACHABILITY.value

    def __init__(self, *, treat_public_as_reachable: bool = True) -> None:
        """Args:
        treat_public_as_reachable: `_` 로 시작하지 않는 이름을 외부 진입점으로
            볼지. 🔴 손잡이다 - 끄면 라이브러리 공개 API 가 전부 죽은 코드가 된다.
        """
        self.treat_public_as_reachable = treat_public_as_reachable

    def config_signature(self) -> str:
        return f"reachability(public_entry={self.treat_public_as_reachable})"

    def verify(self, finding: Finding, target: ReviewTarget) -> Evidence:
        src = target.file(finding.location.path)
        if src is None:
            return self._na("제시된 파일이 아니다")
        try:
            tree = ast.parse(src.content)
        except SyntaxError:
            return self._na("파싱할 수 없다")

        symbol = finding.location.symbol
        if not symbol:
            return self._na("모듈 최상위 - 항상 실행된다")

        leaf = symbol.rsplit(".", maxsplit=1)[-1]
        if self.treat_public_as_reachable and not leaf.startswith("_"):
            return Evidence(
                kind=EvidenceKind.REACHABILITY,
                verdict=Verdict.SUPPORTS,
                detail=f"{symbol} 은 공개 이름이라 파일 밖에서 불릴 수 있다",
            )

        referenced = self._referenced_names(tree, exclude_def=leaf)
        if leaf in referenced:
            return Evidence(
                kind=EvidenceKind.REACHABILITY,
                verdict=Verdict.SUPPORTS,
                detail=f"{symbol} 이 파일 안에서 참조된다",
            )

        # 🔴 REFUTES 를 내되 근거의 한계를 같이 적는다.
        return Evidence(
            kind=EvidenceKind.REACHABILITY,
            verdict=Verdict.REFUTES,
            detail=(
                f"{symbol} 이 제시된 파일 안에서 참조되지 않는다 - "
                "죽은 코드일 수 있다. 단 파일 밖 호출과 동적 호출은 보지 못한다"
            ),
        )

    def _referenced_names(self, tree: ast.Module, exclude_def: str) -> frozenset[str]:
        """정의 자체를 뺀 참조 이름들."""
        defined_at: set[int] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                and node.name == exclude_def
            ):
                defined_at.add(id(node))

        names: set[str] = set()
        for node in ast.walk(tree):
            if id(node) in defined_at:
                continue
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        return frozenset(names)

    def _na(self, why: str) -> Evidence:
        return Evidence(
            kind=EvidenceKind.REACHABILITY,
            verdict=Verdict.NOT_APPLICABLE,
            detail=why,
        )
