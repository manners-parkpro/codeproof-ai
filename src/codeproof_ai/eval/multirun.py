"""다회 실행의 짝 채점 — 합집합으로 뭉개지 않고 **라벨 붙인 관점**으로 낸다 (F3 · F6).

N회 실행이면 한 짝에 대한 답이 N개다. 그걸 하나로 접는 방법마다 숫자가 다르고,
그 차이가 곧 측정 대상이다:

    단일 실행 기대값   실행마다 짝 채점 → 평균. 개발자가 **한 번** 돌렸을 때의 기대값.
    k-임계            k회 이상 나온 지적만 센다. k=1 이 합집합, k=N 이 만장일치.
                      🔴 N회 실행을 요구하는 **기법**이지 기준선이 아니다.

🔴 합집합(k=1)만 내면 드물게 튀는 지적 하나가 짝을 P-V 로 만든다 - 과잉지적이
   부풀고, 그 숫자는 개발자가 한 번 돌려서는 볼 수 없는 값이다.

## 신뢰구간

단일 실행 기대값의 구간은 **짝 단위 부트스트랩**이다. 같은 짝을 N번 본 것이라
실행끼리 독립이 아니고, 모집단에서 뽑은 표본은 짝이다. 짝마다 「N회 중 구별한
비율」을 하나로 두고 짝을 복원추출한다. 🔴 시드를 고정한다 - 생성물은 결정적이어야
「최신인가」를 물을 수 있다 (F5b).

k-임계는 짝마다 예/아니오 하나라 Wilson 구간이다 (`Proportion`).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import fmean
from typing import TYPE_CHECKING

from codeproof_ai.eval.metrics import Proportion
from codeproof_ai.eval.pairing import PairVerdict, discrimination_rate, score_pairs

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.runner import SampleOutcome

RESAMPLES = 2000
SEED = 0


@dataclass(frozen=True, slots=True)
class Expectation:
    """단일 실행 기대값 - 실행별 구별 성공(P-C)의 평균."""

    per_run: tuple[int, ...]
    """실행별 P-C 개수. 🔴 폭이 측정 대상이다 - 같은 설정의 모델 실행은 흔들린다 (F1)."""

    pairs: int
    point: float | None
    interval: tuple[float, float] | None
    """짝 단위 부트스트랩 95%."""

    def render(self) -> str:
        if self.point is None or self.interval is None:
            return "n/a (짝 0)"
        lo, hi = self.interval
        spread = f"{min(self.per_run)}~{max(self.per_run)}"
        return (
            f"{self.point:6.1%}  [{lo:5.1%}, {hi:5.1%}]  "
            f"실행별 {spread}/{self.pairs}  ({len(self.per_run)}회)"
        )


def total_runs(outcomes: Sequence[SampleOutcome]) -> int:
    """실행 횟수. 🔴 샘플마다 다르면 거부한다 - 모자란 실행은 「지적 0건」으로 읽힌다."""
    counts = {o.observations.total_runs for o in outcomes}
    if len(counts) != 1:
        msg = f"샘플마다 실행 횟수가 다르다: {sorted(counts)} - 완전한 짝만 넘긴다"
        raise ValueError(msg)
    return counts.pop()


def expectation(
    outcomes: Sequence[SampleOutcome],
    grader: str,
    *,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Expectation:
    """실행마다 짝 채점을 하고 평균한다. 구간은 짝 단위 부트스트랩."""
    runs = total_runs(outcomes)
    by_run = [score_pairs(outcomes, grader, run=r) for r in range(runs)]
    pair_ids = [p.pair_id for p in by_run[0]]
    if not pair_ids:
        return Expectation(per_run=(), pairs=0, point=None, interval=None)

    hits = dict.fromkeys(pair_ids, 0)
    for results in by_run:
        for pr in results:
            if pr.verdict is PairVerdict.CORRECT:
                hits[pr.pair_id] += 1
    shares = [hits[p] / runs for p in pair_ids]

    rng = random.Random(seed)  # noqa: S311 - 재표집용이다. 보안 난수가 아니고 재현이 목적이다
    boots = sorted(fmean(rng.choices(shares, k=len(shares))) for _ in range(resamples))
    lo = boots[round(0.025 * (resamples - 1))]
    hi = boots[round(0.975 * (resamples - 1))]
    per_run = tuple(
        sum(1 for pr in results if pr.verdict is PairVerdict.CORRECT) for results in by_run
    )
    return Expectation(per_run=per_run, pairs=len(pair_ids), point=fmean(shares), interval=(lo, hi))


def thresholds(runs: int) -> tuple[tuple[str, int], ...]:
    """k-임계 관점들 - (라벨, k). 1회 실행이면 관점이 하나뿐이다."""
    if runs == 1:
        return (("1회", 1),)
    # 겹치면 앞의 라벨이 남는다 - 2회에서 과반은 곧 만장일치다.
    candidates = [
        ("k≥1 (합집합)", 1),
        (f"k={runs} (만장일치)", runs),
        (f"k≥{runs // 2 + 1} (과반)", runs // 2 + 1),
    ]
    views: dict[int, str] = {}
    for label, k in candidates:
        views.setdefault(k, label)
    return tuple((views[k], k) for k in sorted(views))


def at_least(outcomes: Sequence[SampleOutcome], grader: str, k: int) -> Proportion:
    """k회 이상 나온 지적만 셌을 때의 구별 성공 - Wilson 구간."""
    hit, total = discrimination_rate(score_pairs(outcomes, grader, at_least=k))
    return Proportion(hit, total)
