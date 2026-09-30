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
from codeproof_ai.eval.pairing import PairVerdict, pair_summary, score_pairs
from codeproof_ai.eval.runner import SampleOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.eval.sample import LabeledSample

DEFAULT_SWEEP: tuple[int, ...] = (0, 2, 5)


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
