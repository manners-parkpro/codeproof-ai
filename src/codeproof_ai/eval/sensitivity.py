"""매칭 민감도 - 판정이 손잡이에 얼마나 흔들리는가.

[실측] 같은 결함을 Ruff 는 호출 시작 줄(L9)로, bandit 은 `shell=True` 인자 줄(L11)로
       보고한다. 결함 구간이 5-10 이면 slack=0 에서 한쪽만 TP 가 된다 -
       **리뷰 품질 차이가 아니라 보고 관례 차이다.**

그래서 단일 slack 값으로 낸 숫자는 신뢰할 수 없다. 스윕해서 **흔들리는지**를 같이 낸다.
흔들리면 그 결론은 매칭 정책의 산물이지 리뷰어의 성질이 아니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.multirun import (
    EXPECTATION_LABEL,
    at_least,
    expectation,
    thresholds,
    total_runs,
)
from codeproof_ai.eval.pairing import PairVerdict, pair_summary, score_pairs
from codeproof_ai.eval.runner import SampleOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.metrics import Proportion
    from codeproof_ai.eval.sample import LabeledSample

# 🔴 (0,2,5) 는 좁다 - 전이점이 slack 6 으로 옮겨가자 안정으로 보였다 (DESIGN #31).
#    [실측 · 60쌍] ruff S,B,F,SIM 은 (0,2,5) 에서 stable, 10 을 넣으면 5→10 에서 바뀐다.
DEFAULT_SWEEP: tuple[int, ...] = (0, 2, 5, 10)


def regrade_safety(
    outcomes: Sequence[SampleOutcome], samples: Sequence[LabeledSample], slack: int
) -> list[SampleOutcome]:
    """지적은 그대로 두고 `provable_safety` 만 slack 을 바꿔 다시 채점한다.

    🔴 import 출력과 생성물이 **같은 함수**로 스윕한다 - 한 곳만 다르면 같은 실행이
       곳마다 다른 민감도를 낸다 (A2a).
    """
    by_id = {s.sample_id: s for s in samples}
    g = ProvableSafetyGrader(overlap_slack=slack)
    return [
        SampleOutcome(
            sample_id=o.sample_id,
            is_proven_safe=o.is_proven_safe,
            observations=o.observations,
            judgments={g.name: tuple(g.judge(by_id[o.sample_id], o.observations.observed))},
        )
        for o in outcomes
        if o.sample_id in by_id
    ]


@dataclass(frozen=True, slots=True)
class ViewPoint:
    slack: int
    expectation: float
    """단일 실행 기대값 (점추정)."""
    thresholds: tuple[Proportion, ...]
    """k-임계마다 - `ViewSweep.thresholds` 와 같은 순서."""


@dataclass(frozen=True, slots=True)
class ViewSweep:
    """관점마다 slack 을 바꿔 다시 채점한 구별 성공(P-C) - 다회 실행용.

    🔴 `sweep()` 은 관점을 모르고 합집합으로 센다. 다회 실행이면 이것을 쓴다 (F6).
    """

    thresholds: tuple[str, ...]
    """k-임계 관점의 이름 - `multirun.thresholds()` 의 순서."""
    points: tuple[ViewPoint, ...]

    @property
    def moved(self) -> tuple[str, ...]:
        """구별 성공이 slack 에 따라 바뀐 관점.

        🔴 반올림 전 값으로 판정한다 - 표의 63.5% 둘이 실제로는 다를 수 있다.
        """
        columns = [
            (EXPECTATION_LABEL, [p.expectation for p in self.points]),
            *(
                (label, [float(p.thresholds[i].successes) for p in self.points])
                for i, label in enumerate(self.thresholds)
            ),
        ]
        return tuple(label for label, values in columns if len(set(values)) > 1)


def sweep_views(
    outcomes: Sequence[SampleOutcome],
    samples: Sequence[LabeledSample],
    slacks: Sequence[int] = DEFAULT_SWEEP,
) -> ViewSweep | None:
    """다회 실행의 slack 스윕 - `provable_safety` 의 구별 성공을 관점마다 낸다. 짝이 없으면 None.

    🔴 생성물과 import · eval 출력이 **이 함수 하나**로 낸다 (A2a).
    """
    views = thresholds(total_runs(outcomes))
    points: list[ViewPoint] = []
    for slack in slacks:
        g = ProvableSafetyGrader(overlap_slack=slack)
        point = expectation(outcomes, samples, g).point
        if point is None:
            return None
        points.append(
            ViewPoint(slack, point, tuple(at_least(outcomes, samples, g, k) for _, k in views))
        )
    return ViewSweep(thresholds=tuple(label for label, _ in views), points=tuple(points))


@dataclass(frozen=True, slots=True)
class SlackPoint:
    slack: int
    correct: int
    over_flag: int
    under_flag: int
    reversed_: int

    @property
    def signature(self) -> tuple[int, int, int, int]:
        return (self.correct, self.over_flag, self.under_flag, self.reversed_)


@dataclass(frozen=True, slots=True)
class Sensitivity:
    grader: str
    points: tuple[SlackPoint, ...]

    @property
    def stable(self) -> bool:
        """모든 slack 에서 같은 판정 분포인가.

        🔴 불안정하면 단일 값으로 낸 숫자를 결론으로 쓰면 안 된다.
        """
        return len({p.signature for p in self.points}) <= 1

    @property
    def flips(self) -> tuple[tuple[int, int], ...]:
        """판정이 바뀐 구간들 (이전 slack, 다음 slack)."""
        out: list[tuple[int, int]] = []
        for a, b in zip(self.points, self.points[1:], strict=False):
            if a.signature != b.signature:
                out.append((a.slack, b.slack))
        return tuple(out)


def _count(outcomes: Sequence[SampleOutcome], grader: str) -> SlackPoint | None:
    pairs = score_pairs(outcomes, grader)
    if not pairs:
        return None
    c = pair_summary(pairs)
    return SlackPoint(
        slack=-1,
        correct=c[PairVerdict.CORRECT],
        over_flag=c[PairVerdict.OVER_FLAG],
        under_flag=c[PairVerdict.UNDER_FLAG],
        reversed_=c[PairVerdict.REVERSED],
    )


def sweep(
    regrade: object,  # Callable[[int], Sequence[SampleOutcome]]
    grader_name: str,
    slacks: Sequence[int] = DEFAULT_SWEEP,
) -> Sensitivity:
    """slack 값마다 다시 채점해 판정 분포를 모은다.

    Args:
        regrade: slack 을 받아 SampleOutcome 들을 돌려주는 호출가능 객체.
            지적을 다시 내지 않고 **채점만** 다시 한다 - 리뷰어를 다시 돌리면
            확률적 리뷰어에서 slack 효과와 실행 변동이 섞인다.
    """
    if not callable(regrade):
        msg = "regrade 는 호출 가능해야 한다"
        raise TypeError(msg)

    points: list[SlackPoint] = []
    for s in slacks:
        outcomes = regrade(s)
        pt = _count(outcomes, grader_name)
        if pt is not None:
            points.append(
                SlackPoint(
                    slack=s,
                    correct=pt.correct,
                    over_flag=pt.over_flag,
                    under_flag=pt.under_flag,
                    reversed_=pt.reversed_,
                )
            )
    return Sensitivity(grader=grader_name, points=tuple(points))
