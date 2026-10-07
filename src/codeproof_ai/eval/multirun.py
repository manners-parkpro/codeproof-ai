"""다회 실행의 짝 채점 — 합집합으로 뭉개지 않고 **라벨 붙인 관점**으로 낸다 (F3 · F6).

N회 실행이면 한 짝에 대한 답이 N개다. 그걸 하나로 접는 방법마다 숫자가 다르고,
그 차이가 곧 측정 대상이다:

    단일 실행 기대값   실행마다 짝 채점 → 평균. 개발자가 **한 번** 돌렸을 때의 기대값.
    k-임계            k회 이상 나온 지적만 센다. k=1 이 합집합, k=N 이 만장일치.
                      🔴 N회 실행을 요구하는 **기법**이지 기준선이 아니다.

🔴 합집합(k=1)만 내면 드물게 튀는 지적 하나가 짝을 P-V 로 만든다 - 과잉지적이
   부풀고, 그 숫자는 개발자가 한 번 돌려서는 볼 수 없는 값이다.

🔴 관점별 숫자는 판정을 걸러내지 않고 **관점의 지적만으로 다시 채점**한다
   (`runner.regrade_view`). 짝의 지적을 받는 채점자(paired_fix)는 합집합 짝으로
   판정했으므로, 걸러내기만 하면 그 판정이 관점에 그대로 남는다
   [실측 · claude n=8 · 60쌍: 60.4% 로 발표 · 회차별 단독 채점 62.7%].

## 신뢰구간

단일 실행 기대값의 구간은 **짝 단위 부트스트랩**이다. 같은 짝을 N번 본 것이라
실행끼리 독립이 아니고, 모집단에서 뽑은 표본은 짝이다. 짝마다 「N회 중 구별한
비율」을 하나로 두고 짝을 복원추출한다. 🔴 시드를 고정한다 - 생성물은 결정적이어야
「최신인가」를 물을 수 있다 (F5b).

k-임계는 짝마다 예/아니오 하나라 Wilson 구간이다 (`Proportion`).

## 판정 묶음

기본은 구별 성공(P-C) 하나다 - 수집 전에 선언한 주 지표다 (DESIGN §7.10b).
점수판의 「짚음」(P-C · P-V) · 「헛경고」(P-V · P-R)도 **같은 짝 판정을 다시 묶은 것**이라
같은 관점 · 같은 구간으로 낸다 (`hits`).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import fmean
from typing import TYPE_CHECKING

from codeproof_ai.eval.metrics import Proportion
from codeproof_ai.eval.pairing import PairVerdict, discrimination_rate, score_pairs
from codeproof_ai.eval.runner import regrade_view

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.eval.grading.base import Grader
    from codeproof_ai.eval.runner import SampleOutcome
    from codeproof_ai.eval.sample import LabeledSample

RESAMPLES = 2000
SEED = 0

# 단일 실행 기대값 관점의 이름 - k-임계 관점의 이름은 `thresholds()` 가 낸다.
EXPECTATION_LABEL = "단일 실행 기대값"

CORRECT_ONLY = frozenset({PairVerdict.CORRECT})
"""기본 판정 묶음 - 구별 성공(P-C)."""


@dataclass(frozen=True, slots=True)
class Expectation:
    """단일 실행 기대값 - 실행별로 판정 묶음(`hits`)에 든 짝 비율의 평균. 기본은 P-C."""

    per_run: tuple[int, ...]
    """실행별로 묶음에 든 짝 수. 🔴 폭이 측정 대상이다 - 같은 설정의 모델 실행은 흔들린다 (F1)."""

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


def verdicts_by_run(
    outcomes: Sequence[SampleOutcome], samples: Sequence[LabeledSample], grader: Grader
) -> list[dict[str, PairVerdict]]:
    """실행마다 **그 실행의 지적만으로 다시 채점한** 짝 판정.

    판정 묶음 여럿을 셀 때 한 번만 채점한다 - `expectation_of` · `difference_of` 가 받는다.
    """
    return [
        {
            pr.pair_id: pr.verdict
            for pr in score_pairs(regrade_view(outcomes, samples, [grader], run=r), grader.name)
        }
        for r in range(total_runs(outcomes))
    ]


def _shares(
    by_run: Sequence[Mapping[str, PairVerdict]], hits: frozenset[PairVerdict]
) -> dict[str, float]:
    """짝마다 「N회 중 묶음에 든 비율」 하나 - 부트스트랩이 복원추출하는 단위다."""
    runs = len(by_run)
    return {p: sum(r[p] in hits for r in by_run) / runs for p in by_run[0]}


def _interval(values: list[float], *, resamples: int, seed: int) -> tuple[float, float]:
    """짝 단위 부트스트랩 95%."""
    rng = random.Random(seed)  # noqa: S311 - 재표집용이다. 보안 난수가 아니고 재현이 목적이다
    boots = sorted(fmean(rng.choices(values, k=len(values))) for _ in range(resamples))
    return boots[round(0.025 * (resamples - 1))], boots[round(0.975 * (resamples - 1))]


def expectation(
    outcomes: Sequence[SampleOutcome],
    samples: Sequence[LabeledSample],
    grader: Grader,
    *,
    hits: frozenset[PairVerdict] = CORRECT_ONLY,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Expectation:
    """실행마다 **그 실행의 지적만으로 다시 채점해** 짝을 매기고 평균한다.

    구간은 짝 단위 부트스트랩.
    """
    return expectation_of(
        verdicts_by_run(outcomes, samples, grader), hits, resamples=resamples, seed=seed
    )


def expectation_of(
    by_run: Sequence[Mapping[str, PairVerdict]],
    hits: frozenset[PairVerdict] = CORRECT_ONLY,
    *,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Expectation:
    """이미 채점한 실행별 짝 판정(`verdicts_by_run`)으로 낸 단일 실행 기대값."""
    shares = list(_shares(by_run, hits).values()) if by_run else []
    if not shares:
        return Expectation(per_run=(), pairs=0, point=None, interval=None)
    per_run = tuple(sum(v in hits for v in r.values()) for r in by_run)
    interval = _interval(shares, resamples=resamples, seed=seed)
    return Expectation(per_run=per_run, pairs=len(shares), point=fmean(shares), interval=interval)


def mean_share(
    by_run: Sequence[Mapping[str, PairVerdict]], hits: frozenset[PairVerdict] = CORRECT_ONLY
) -> float | None:
    """단일 실행 기대값의 점추정만 - 구간이 필요 없는 자리에서 부트스트랩을 건너뛴다."""
    shares = list(_shares(by_run, hits).values()) if by_run else []
    return fmean(shares) if shares else None


@dataclass(frozen=True, slots=True)
class Difference:
    """두 리뷰어의 단일 실행 기대값 차이 (a - b) - 같은 짝 위에서."""

    pairs: int
    point: float | None
    interval: tuple[float, float] | None
    """짝 단위 부트스트랩 95% - 두 리뷰어를 **같은 짝으로 함께** 복원추출한다."""

    @property
    def distinguishable(self) -> bool | None:
        """구간이 0 을 품지 않는가.

        🔴 두 리뷰어의 구간을 눈으로 겹쳐 보는 것과 다르다 - 같은 짝을 함께 뽑으면
           짝마다의 난이도가 상쇄되어 그보다 예민하다.
        """
        if self.interval is None:
            return None
        lo, hi = self.interval
        return lo > 0 or hi < 0


def difference(
    a: Sequence[SampleOutcome],
    b: Sequence[SampleOutcome],
    samples: Sequence[LabeledSample],
    grader: Grader,
    *,
    hits: frozenset[PairVerdict] = CORRECT_ONLY,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Difference:
    """두 리뷰어의 단일 실행 기대값 차이 (a - b).

    실행 횟수는 달라도 된다 - 단일 실행 기대값은 N 과 무관한 양이다.
    🔴 짝 집합이 다르면 거부한다. 한쪽에만 있는 짝을 빼고 비교하면 비교 대상이
       조용히 바뀐다.
    """
    return difference_of(
        verdicts_by_run(a, samples, grader),
        verdicts_by_run(b, samples, grader),
        hits,
        resamples=resamples,
        seed=seed,
    )


def difference_of(
    a: Sequence[Mapping[str, PairVerdict]],
    b: Sequence[Mapping[str, PairVerdict]],
    hits: frozenset[PairVerdict] = CORRECT_ONLY,
    *,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Difference:
    """이미 채점한 실행별 짝 판정(`verdicts_by_run`) 둘의 차이 (a - b)."""
    sa = _shares(a, hits) if a else {}
    sb = _shares(b, hits) if b else {}
    if sa.keys() != sb.keys():
        msg = f"두 리뷰어의 짝이 다르다 ({len(sa)} vs {len(sb)}) - 같은 짝 위에서만 비교한다"
        raise ValueError(msg)
    if not sa:
        return Difference(pairs=0, point=None, interval=None)
    diffs = [sa[p] - sb[p] for p in sa]
    interval = _interval(diffs, resamples=resamples, seed=seed)
    return Difference(pairs=len(diffs), point=fmean(diffs), interval=interval)


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


def at_least(
    outcomes: Sequence[SampleOutcome],
    samples: Sequence[LabeledSample],
    grader: Grader,
    k: int,
) -> Proportion:
    """k회 이상 나온 지적만으로 다시 채점했을 때의 구별 성공 - Wilson 구간."""
    view = regrade_view(outcomes, samples, [grader], at_least=k)
    hit, total = discrimination_rate(score_pairs(view, grader.name))
    return Proportion(hit, total)
