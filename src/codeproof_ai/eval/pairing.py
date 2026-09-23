"""짝 채점 - PrimeVul P-C/P-V/P-B/P-R.

🔴 **과잉지적은 짝을 지어야만 보인다.**

지적 단위로 보면 "decoy 에서 FP 1건, twin 에서 TP 1건" 이 Precision 50% 로 읽힌다.
그러나 그 둘이 **같은 룰 · 같은 줄** 이면 탐지 능력이 아니라 패턴 매칭이다 -
안전한 쪽과 터지는 쪽을 구별하지 못한 것이고, twin 의 TP 는 맞는 이유로 맞은 게
아니라 틀린 이유로 우연히 맞은 것이다.

PrimeVul 에서 7B SOTA 모델이 BigVul F1 68.26% -> 3.09% 로 무너진 게 이 채점 때문이다.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Outcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.runner import SampleOutcome


class PairVerdict(StrEnum):
    """짝 하나에 대한 판정."""

    CORRECT = "P-C"
    """양성은 잡고 음성은 안 잡았다. **유일하게 옳은 결과.**"""

    OVER_FLAG = "P-V"
    """둘 다 잡았다 - 구별하지 못했다. **과잉지적.**"""

    UNDER_FLAG = "P-B"
    """둘 다 안 잡았다 - 진짜 결함을 놓쳤다."""

    REVERSED = "P-R"
    """음성만 잡았다 - 정확히 거꾸로다."""


@dataclass(frozen=True, slots=True)
class PairResult:
    pair_id: str
    verdict: PairVerdict
    negative_flagged: bool
    positive_flagged: bool
    detail: str = ""


def _flagged(outcome: SampleOutcome, grader: str, *, want: Outcome) -> bool:
    """이 샘플에서 채점자가 관련 지적을 인정했는가.

    음성에서는 FALSE_POSITIVE 가, 양성에서는 TRUE_POSITIVE 가
    "리뷰어가 이 자리를 지적했다" 를 뜻한다.
    UNDECIDABLE 은 **지적하지 않은 것으로 세지 않는다** - 판정 범위 밖일 뿐이다.
    """
    return any(j.outcome is want for j in outcome.judgments.get(grader, ()))


def score_pairs(
    outcomes: Sequence[SampleOutcome], grader: str
) -> tuple[PairResult, ...]:
    """음성/양성 짝을 찾아 PrimeVul 코드를 매긴다.

    짝은 `<id>` 와 `<id>#twin` 규약으로 맺는다.
    """
    by_id = {o.sample_id: o for o in outcomes}
    results: list[PairResult] = []

    for o in outcomes:
        if not o.is_proven_safe:
            continue
        twin = by_id.get(f"{o.sample_id}#twin")
        if twin is None:
            continue

        neg = _flagged(o, grader, want=Outcome.FALSE_POSITIVE)
        pos = _flagged(twin, grader, want=Outcome.TRUE_POSITIVE)

        if pos and not neg:
            verdict, detail = PairVerdict.CORRECT, "양성만 지적 - 구별했다"
        elif pos and neg:
            verdict, detail = (
                PairVerdict.OVER_FLAG,
                "둘 다 지적 - 안전한 쪽과 터지는 쪽을 구별하지 못했다",
            )
        elif not pos and not neg:
            verdict, detail = PairVerdict.UNDER_FLAG, "둘 다 미지적 - 결함을 놓쳤다"
        else:
            verdict, detail = PairVerdict.REVERSED, "음성만 지적 - 거꾸로다"

        results.append(
            PairResult(
                pair_id=o.sample_id,
                verdict=verdict,
                negative_flagged=neg,
                positive_flagged=pos,
                detail=detail,
            )
        )
    return tuple(results)


def pair_summary(results: Sequence[PairResult]) -> Counter[PairVerdict]:
    return Counter(r.verdict for r in results)


def discrimination_rate(results: Sequence[PairResult]) -> tuple[int, int]:
    """(구별 성공, 전체). 🔴 이게 짝 채점의 헤드라인이다."""
    return sum(1 for r in results if r.verdict is PairVerdict.CORRECT), len(results)
