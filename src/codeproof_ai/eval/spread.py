"""채점 기준 편차 - 이 프로젝트의 헤드라인.

같은 Finding 집합을 여러 정답 정의에 통과시키고 **결과가 얼마나 갈리는지**를 낸다.

발표된 Precision 이 정답 정의에 따라 20배 차이 나는데(CR-Bench 3.5% ~ Qodo 79%)
아무도 그 편차를 재지 않았다는 것이 이 프로젝트의 빈칸이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Outcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.runner import SampleOutcome


@dataclass(frozen=True, slots=True)
class GraderColumn:
    """한 채점자가 같은 지적 집합에 내린 결과."""

    grader: str
    definition: str
    true_positive: int
    false_positive: int
    undecidable: int
    can_emit_fp: bool = True
    """🔴 이 채점자가 FP 를 낼 수 **있는가**.

    못 내는 채점자의 0 을 편차에 넣으면 범주 차이를 편차로 오해한다.
    """

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.undecidable

    @property
    def decided(self) -> int:
        return self.true_positive + self.false_positive


@dataclass(frozen=True, slots=True)
class Spread:
    """여러 채점자를 나란히 세운 결과."""

    findings: int
    """채점된 고유 지적 수. **모든 채점자가 같은 집합을 본다.**"""

    columns: tuple[GraderColumn, ...]

    @property
    def comparable(self) -> tuple[GraderColumn, ...]:
        """FP 를 낼 수 있는 채점자만. 편차는 이들끼리만 계산한다."""
        return tuple(c for c in self.columns if c.can_emit_fp)

    @property
    def fp_range(self) -> tuple[int, int]:
        vals = [c.false_positive for c in self.comparable]
        return (min(vals), max(vals)) if vals else (0, 0)

    @property
    def fp_ratio(self) -> float | None:
        """최대 FP / 최소 FP. 🔴 이 값이 편차의 크기다.

        최소가 0 이면 비율이 정의되지 않는다 - None 을 낸다.
        「무한대」로 부풀리지 않는다.
        """
        lo, hi = self.fp_range
        return hi / lo if lo > 0 else None

    @property
    def disagreement(self) -> int:
        """최대 FP 와 최소 FP 의 차이. 정의 선택만으로 생긴 FP 수다."""
        lo, hi = self.fp_range
        return hi - lo


def compute_spread(
    outcomes: Sequence[SampleOutcome],
    definitions: dict[str, str],
    fp_capable: set[str] | None = None,
    *,
    negatives_only: bool = False,
) -> Spread:
    """같은 지적 집합에 대한 채점자별 결과를 모은다.

    Args:
        negatives_only: 증명된 음성 샘플만 본다.
            FP 편차는 음성 위에서 가장 선명하다 - 양성 위의 차이는
            결함 위치 매칭의 차이라 성질이 다르다.
    """
    subset = [o for o in outcomes if not negatives_only or o.is_proven_safe]
    findings = sum(len(o.observations.observed) for o in subset)

    columns: list[GraderColumn] = []
    for grader, definition in definitions.items():
        tp = fp = un = 0
        for o in subset:
            for j in o.judgments.get(grader, ()):
                if j.outcome is Outcome.TRUE_POSITIVE:
                    tp += 1
                elif j.outcome is Outcome.FALSE_POSITIVE:
                    fp += 1
                else:
                    un += 1
        columns.append(
            GraderColumn(
                grader=grader,
                definition=definition,
                true_positive=tp,
                false_positive=fp,
                undecidable=un,
                can_emit_fp=fp_capable is None or grader in fp_capable,
            )
        )

    return Spread(findings=findings, columns=tuple(columns))
