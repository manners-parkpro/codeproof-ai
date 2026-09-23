"""근거 집계 - confidence 는 확률이 아니다.

🔴 이 값을 「정답일 확률」로 읽으면 안 된다.
   라벨을 보지 않고 계산했으므로 어디까지나 **모인 근거의 양**이다.
   정답 대조는 eval/ 의 Grader 가 하고, 그건 완전히 다른 층이다.

가중치는 전부 **임의의 선택**이다. 임의인 것을 숨기지 않고 드러낸다 -
`config_signature()` 로 매니페스트에 실려 재현과 재검토가 가능하다.
숫자에 근거가 있는 척하는 것보다 임의임을 적는 쪽이 정직하다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.domain.evidence import (
    Evidence,
    EvidenceKind,
    Verdict,
    VerifiedFinding,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget
    from codeproof_ai.verify.base import Verifier


@dataclass(frozen=True, slots=True)
class Weights:
    """근거 종류별 기여도. **임의값이다.**

    바꾸면 confidence 가 바뀌므로 매니페스트에 실린다.
    """

    base: float = 0.5
    citation: float = 0.2
    guard: float = 0.3
    corroboration: float = 0.2
    reachability: float = 0.15

    def of(self, kind: EvidenceKind) -> float:
        return {
            EvidenceKind.CITATION: self.citation,
            EvidenceKind.GUARD: self.guard,
            EvidenceKind.CORROBORATION: self.corroboration,
            EvidenceKind.REACHABILITY: self.reachability,
        }.get(kind, 0.0)

    def signature(self) -> str:
        return (
            f"b{self.base}/c{self.citation}/g{self.guard}"
            f"/x{self.corroboration}/r{self.reachability}"
        )


def aggregate(evidence: Sequence[Evidence], weights: Weights | None = None) -> float:
    """근거를 [0,1] 값으로 모은다.

    🔴 하드 게이트가 하나 있다 - **인용이 반박되면 0 이다.**
       가중합이 아니다. 존재하지 않는 코드에 대한 지적이라면
       다른 어떤 근거도 의미가 없기 때문이다.
    """
    w = weights or Weights()

    for ev in evidence:
        if ev.kind is EvidenceKind.CITATION and ev.verdict is Verdict.REFUTES:
            return 0.0

    score = w.base
    for ev in evidence:
        delta = w.of(ev.kind)
        if ev.verdict is Verdict.SUPPORTS:
            score += delta
        elif ev.verdict is Verdict.REFUTES:
            score -= delta
        # INCONCLUSIVE·NOT_APPLICABLE 은 움직이지 않는다 -
        # 「확인 못 함」이 점수를 깎으면 그건 반박으로 세는 것이다.
    return max(0.0, min(1.0, score))


class VerificationPipeline:
    """검증자들을 순서대로 돌려 VerifiedFinding 을 만든다."""

    def __init__(
        self, verifiers: Sequence[Verifier], weights: Weights | None = None
    ) -> None:
        self.verifiers = tuple(verifiers)
        self.weights = weights or Weights()

    def config_signature(self) -> str:
        parts = [v.config_signature() for v in self.verifiers]
        return f"verify[{';'.join(parts)}]w({self.weights.signature()})"

    def run(self, finding: Finding, target: ReviewTarget) -> VerifiedFinding:
        evidence: list[Evidence] = []
        for v in self.verifiers:
            try:
                evidence.append(v.verify(finding, target))
            except Exception as exc:
                # 🔴 검증 실패도 결과의 일부다. 예외로 지적을 잃지 않는다.
                evidence.append(
                    Evidence(
                        kind=EvidenceKind(v.kind),
                        verdict=Verdict.INCONCLUSIVE,
                        detail=f"검증자가 실패했다: {type(exc).__name__}: {exc}",
                    )
                )
        return VerifiedFinding(
            finding=finding,
            evidence=tuple(evidence),
            confidence=aggregate(evidence, self.weights),
        )
