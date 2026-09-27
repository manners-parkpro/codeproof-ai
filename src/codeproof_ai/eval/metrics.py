"""지표 - 모든 수치에 신뢰구간을 붙인다.

🔴 점추정만 내는 건 측정이 아니다 (CLAUDE.md 코드 스타일).
🔴 층을 섞어서 집계하지 않는다 (E2).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Outcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.grading.base import Judgment

# 음성 100건 미만이면 FPR 의 Wilson 95% CI 반폭이 ±6pp 를 넘는다.
MIN_CREDIBLE_NEGATIVES = 100

TARGET_NEGATIVES = 150
"""숫자를 **발표**할 때 필요한 표본 크기.

🔴 지금 코퍼스는 이보다 작다. 그건 미완성이 아니라 **선언된 상태**다 -
   현재 크기는 「측정 선택이 숫자를 얼마나 움직이는가」라는 논지를 보이기에
   충분하고, 「이 도구의 오탐률은 X% 다」를 발표하려면 여기까지 채워야 한다.
   둘은 다른 주장이고 필요한 표본도 다르다.
"""

Z_95 = 1.959963984540054


@dataclass(frozen=True, slots=True)
class Proportion:
    """비율 + Wilson 95% 신뢰구간."""

    successes: int
    total: int

    @property
    def point(self) -> float | None:
        return self.successes / self.total if self.total else None

    @property
    def interval(self) -> tuple[float, float] | None:
        """Wilson score interval.

        정규근사(Wald)를 쓰지 않는다 - 비율이 0 이나 1 에 가까우면
        구간이 [0,1] 을 벗어나고, 표본이 작으면 심하게 좁아진다.
        코드리뷰는 정확히 그 영역이다.
        """
        n = self.total
        if n == 0:
            return None
        p = self.successes / n
        z2 = Z_95 * Z_95
        denom = 1 + z2 / n
        center = (p + z2 / (2 * n)) / denom
        margin = (Z_95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
        return max(0.0, center - margin), min(1.0, center + margin)

    @property
    def half_width(self) -> float | None:
        iv = self.interval
        return (iv[1] - iv[0]) / 2 if iv else None

    def render(self) -> str:
        if self.point is None:
            return "n/a (표본 0)"
        iv = self.interval
        assert iv is not None
        return (
            f"{self.point:6.1%}  [{iv[0]:5.1%}, {iv[1]:5.1%}]  "
            f"±{(iv[1] - iv[0]) / 2:4.1%}  n={self.total}"
        )


@dataclass(frozen=True, slots=True)
class GraderResult:
    """한 채점자의 한 층에 대한 결과."""

    grader: str
    definition: str
    stratum: str
    counts: Counter[Outcome]

    @property
    def decided(self) -> int:
        return self.counts[Outcome.TRUE_POSITIVE] + self.counts[Outcome.FALSE_POSITIVE]

    @property
    def precision(self) -> Proportion:
        """판정된 것 중 참인 비율. 🔴 판정 불가는 분모에서 뺀다."""
        return Proportion(self.counts[Outcome.TRUE_POSITIVE], self.decided)

    @property
    def undecidable_rate(self) -> Proportion:
        """🔴 이 값이 크면 그 채점자는 그 층을 못 재는 것이다.

        숨기지 않고 같이 보고한다 - Precision 만 내면
        "판정 못 한 것" 이 사라져 보인다.
        """
        total = sum(self.counts.values())
        return Proportion(self.counts[Outcome.UNDECIDABLE], total)


def summarize(
    grader: str, definition: str, stratum: str, judgments: Sequence[Judgment]
) -> GraderResult:
    return GraderResult(
        grader=grader,
        definition=definition,
        stratum=stratum,
        counts=Counter(j.outcome for j in judgments),
    )


def credibility_warning(negatives: int) -> str | None:
    """표본이 숫자로 취급될 만한지.

    🔴 이 경고는 **끄지 않는다.** 코퍼스가 목표에 못 미치는 것은 알려진
       사실이고, 그 사실이 매 실행마다 보이는 것이 맞다. 경고를 없애려고
       임계값을 낮추면 그 순간 이 프로젝트가 비판하는 일을 하게 된다 -
       기준을 결과에 맞추는 것.
    """
    if negatives >= MIN_CREDIBLE_NEGATIVES:
        return None
    p = Proportion(int(negatives * 0.3), negatives) if negatives else Proportion(0, 0)
    hw = p.half_width
    detail = f" (p=0.30 에서 반폭 ±{hw:.1%})" if hw is not None else ""
    return (
        f"음성 {negatives}건은 {MIN_CREDIBLE_NEGATIVES}건 미만이다{detail}. "
        f"이 구간에서 FPR 은 숫자가 아니라 느낌이다 - 목표 {TARGET_NEGATIVES}건."
    )
