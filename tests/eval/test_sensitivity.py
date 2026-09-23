"""매칭 민감도.

🔴 이 모듈의 존재 이유: [실측] 같은 결함을 Ruff 는 호출 시작 줄(L9)로,
   bandit 은 `shell=True` 인자 줄(L11)로 보고한다. 결함 구간이 5-10 이면
   slack=0 에서 한쪽만 TP 가 된다 - **리뷰 품질 차이가 아니라 보고 관례 차이다.**
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.runner import ReviewerRun, SampleOutcome, run_reviewer
from codeproof_ai.eval.sensitivity import Sensitivity, SlackPoint, sweep

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from codeproof_ai.eval.sample import LabeledSample
    from tests.conftest import AnalyzedCorpus

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


def _regrader(
    run: ReviewerRun, samples: Sequence[LabeledSample]
) -> Callable[[int], list[SampleOutcome]]:
    by_id = {s.sample_id: s for s in samples}

    def regrade(slack: int) -> list[SampleOutcome]:
        g = ProvableSafetyGrader(overlap_slack=slack)
        return [
            SampleOutcome(
                sample_id=o.sample_id,
                is_proven_safe=o.is_proven_safe,
                observations=o.observations,
                judgments={
                    g.name: tuple(g.judge(by_id[o.sample_id], o.observations.observed))
                },
            )
            for o in run.outcomes
        ]

    return regrade


class TestStability:
    def test_identical_points_are_stable(self) -> None:
        pts = tuple(SlackPoint(s, 1, 2, 3, 4) for s in (0, 2, 5))
        assert Sensitivity("g", pts).stable
        assert Sensitivity("g", pts).flips == ()

    def test_differing_points_are_unstable(self) -> None:
        pts = (SlackPoint(0, 0, 0, 9, 1), SlackPoint(2, 0, 1, 9, 0))
        s = Sensitivity("g", pts)
        assert not s.stable
        assert s.flips == ((0, 2),)

    def test_empty_is_trivially_stable(self) -> None:
        assert Sensitivity("g", ()).stable


class TestSweepRegradesWithoutRerunning:
    """🔴 리뷰어를 다시 돌리면 slack 효과와 실행 변동이 섞인다."""

    def test_sweep_uses_the_same_observations(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        run = run_reviewer(
            analyzed("ruff", ("S", "B", "F", "SIM")),
            shipped_samples,
            [ProvableSafetyGrader()],
        )
        calls: list[int] = []

        def counting(slack: int) -> list[SampleOutcome]:
            calls.append(slack)
            return _regrader(run, shipped_samples)(slack)

        sweep(counting, "provable_safety", (0, 2, 5))
        assert calls == [0, 2, 5], "각 slack 마다 채점만 다시 해야 한다"

    def test_rejects_non_callable(self) -> None:
        with pytest.raises(TypeError, match="호출 가능"):
            sweep("not callable", "g")


class TestAgainstShippedCorpus:
    def test_ruff_judgment_is_slack_sensitive(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """🔴 실측 회귀 - 단일 slack 으로 낸 숫자는 결론이 아니다.

        [실측] 전이점은 **코퍼스에 따라 움직인다**. D010 을 재설계하자
        전이가 slack 5 -> 6 으로 옮겨가 (0,2,5) 스윕에서는 안정으로 보였다.
        그건 흔들림이 사라진 게 아니라 **스윕 범위가 좁았던 것**이다.

        그래서 사다리를 (0,2,5,10) 으로 고정한다 - 답을 보고 고른 값이 아니라
        `test_wider_slack_never_reduces_flagging` 과 같은 표준 범위다.
        이 교훈 자체가 논지의 증거다: 측정 손잡이 하나가 결론을 뒤집는다.
        """
        run = run_reviewer(
            analyzed("ruff", ("S", "B", "F", "SIM")),
            shipped_samples,
            [ProvableSafetyGrader()],
        )
        sens = sweep(_regrader(run, shipped_samples), "provable_safety", (0, 2, 5, 10))

        assert len(sens.points) == 4
        assert not sens.stable, (
            "slack 에 흔들리지 않게 됐다면 이 테스트와 문서를 갱신한다 - "
            "매칭이 도구 의존적이라는 근거가 사라진 것이다"
        )
        assert sens.flips, f"판정이 바뀌는 구간이 있어야 한다: {sens.points}"

    def test_wider_slack_never_reduces_flagging(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """slack 을 넓히면 지적이 더 잡히지 덜 잡히지 않는다 - 단조성."""
        run = run_reviewer(
            analyzed("ruff", ("S", "B", "F", "SIM")),
            shipped_samples,
            [ProvableSafetyGrader()],
        )
        sens = sweep(_regrader(run, shipped_samples), "provable_safety", (0, 2, 5, 10))
        undecided = [p.under_flag for p in sens.points]
        assert undecided == sorted(undecided, reverse=True) or len(set(undecided)) == 1
