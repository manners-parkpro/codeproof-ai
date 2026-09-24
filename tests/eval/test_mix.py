"""코퍼스 구성비 민감도.

🔴 이 측정의 위험은 **과장**이다. 분류별 표본이 작아서 「구성비만 바꿔
   0% ~ 55% 를 보고할 수 있다」를 「도구의 오탐률이 0~55% 다」로 읽으면
   우리가 비판하는 바로 그 과장이 된다.

   그래서 여기서 가장 중요한 테스트는 「범위가 넓게 나오는가」가 아니라
   **「이질성을 주장할 수 없을 때 주장하지 않는가」** 다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeproof_ai.domain.observation import group_runs
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.grading.base import Judgment, Outcome
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.mix import (
    TARGET_PAIRS_PER_KIND,
    Axis,
    mix_sensitivity,
)
from codeproof_ai.eval.runner import SampleOutcome, run_reviewer
from codeproof_ai.eval.sample import LabeledSample, SafetyRationale, Stratum

if TYPE_CHECKING:
    from tests.conftest import AnalyzedCorpus

GRADER = "provable_safety"


def _outcome(
    sample_id: str, outcomes: list[Outcome], *, safe: bool = True
) -> SampleOutcome:
    return SampleOutcome(
        sample_id=sample_id,
        is_proven_safe=safe,
        observations=group_runs(sample_id, [[]]),
        judgments={
            GRADER: tuple(
                Judgment(
                    finding_key=f"{sample_id}#{i}",
                    outcome=o,
                    grader=GRADER,
                    rationale="테스트",
                )
                for i, o in enumerate(outcomes)
            )
        },
    )


class TestDenominatorIsAllFindings:
    """🔴 판정된 것만 분모에 넣으면 항상 100% 가 나온다."""

    def test_undecided_stays_in_the_denominator(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        run = run_reviewer(
            analyzed("ruff", ("ALL",)), shipped_samples, [ProvableSafetyGrader()]
        )
        ms = mix_sensitivity(run.outcomes, shipped_samples, GRADER)

        assert ms.observed.point is not None
        assert ms.observed.point < 1.0, (
            "전부 100% 다 - 증명된 음성 위에서는 TP 가 정의상 불가능하므로 "
            "FP/(TP+FP) 는 정보가 없다. 범위 밖 지적이 분모에 남아야 한다."
        )
        assert any(k.undecided > 0 for k in ms.kinds), "범위 밖 지적이 세어지지 않았다"

    def test_findings_equal_bitten_plus_undecided(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        run = run_reviewer(
            analyzed("ruff", ("ALL",)), shipped_samples, [ProvableSafetyGrader()]
        )
        for k in mix_sensitivity(run.outcomes, shipped_samples, GRADER).kinds:
            assert k.rate.total == k.rate.successes + k.undecided


class TestItRefusesToOverclaim:
    """🔴 이 파일의 본체."""

    def test_overlapping_intervals_are_not_called_a_difference(self) -> None:
        """표본이 작아 CI 가 겹치면 **차이를 주장하지 않는다**."""
        outcomes = [
            _outcome("a", [Outcome.FALSE_POSITIVE, Outcome.UNDECIDABLE]),
            _outcome("b", [Outcome.UNDECIDABLE, Outcome.UNDECIDABLE]),
        ]
        samples = _samples({"a": "kind_hi", "b": "kind_lo"})
        ms = mix_sensitivity(outcomes, samples, GRADER)

        assert ms.reachable == (0.0, 0.5), "범위 자체는 계산된다"
        assert "아직 주장할 수 없다" in ms.heterogeneity_verdict

    def test_disjoint_intervals_are_called_real(self) -> None:
        """표본이 충분해 CI 가 갈라지면 실재한다고 말한다."""
        outcomes = [
            _outcome(f"hi{i}", [Outcome.FALSE_POSITIVE] * 10) for i in range(6)
        ] + [_outcome(f"lo{i}", [Outcome.UNDECIDABLE] * 10) for i in range(6)]
        samples = _samples(
            {f"hi{i}": "kind_hi" for i in range(6)}
            | {f"lo{i}": "kind_lo" for i in range(6)}
        )
        ms = mix_sensitivity(outcomes, samples, GRADER)
        assert "실재한다" in ms.heterogeneity_verdict

    def test_single_kind_cannot_claim_heterogeneity(self) -> None:
        ms = mix_sensitivity(
            [_outcome("a", [Outcome.FALSE_POSITIVE])], _samples({"a": "only"}), GRADER
        )
        assert "판정 불가" in ms.heterogeneity_verdict

    def test_ratio_is_none_when_minimum_is_zero(self) -> None:
        """0 으로 나누어 「무한대 배」로 부풀리지 않는다 - spread 와 같은 규칙."""
        outcomes = [
            _outcome("a", [Outcome.FALSE_POSITIVE]),
            _outcome("b", [Outcome.UNDECIDABLE]),
        ]
        ms = mix_sensitivity(outcomes, _samples({"a": "hi", "b": "lo"}), GRADER)
        assert ms.reachable == (0.0, 1.0)
        assert ms.ratio is None


class TestOptionalStoppingIsGuarded:
    """🔴 CI 가 갈릴 때까지 표본을 늘리다 멈추면 통계적 부정이다.

    구성비 표를 보면 「이 두 분류만 늘리면 갈리겠다」가 바로 보인다.
    그 유혹을 막으려고 **분류당 목표치를 미리 선언**하고, 미달 상태의
    판정은 결론이 아니라 중간 경과라고 표시한다.
    """

    def test_underpowered_kinds_are_listed(self) -> None:
        outcomes = [
            _outcome("a", [Outcome.FALSE_POSITIVE]),
            _outcome("b", [Outcome.UNDECIDABLE]),
        ]
        ms = mix_sensitivity(outcomes, _samples({"a": "hi", "b": "lo"}), GRADER)
        assert set(ms.underpowered_kinds) == {"hi", "lo"}

    def test_a_separated_verdict_is_still_marked_provisional(self) -> None:
        """목표 미달인데 갈렸으면 **결론이 아니라고** 말한다."""
        outcomes = [
            _outcome(f"hi{i}", [Outcome.FALSE_POSITIVE] * 10) for i in range(6)
        ] + [_outcome(f"lo{i}", [Outcome.UNDECIDABLE] * 10) for i in range(6)]
        samples = _samples(
            {f"hi{i}": "kind_hi" for i in range(6)}
            | {f"lo{i}": "kind_lo" for i in range(6)}
        )
        ms = mix_sensitivity(outcomes, samples, GRADER)

        assert "실재한다" in ms.heterogeneity_verdict
        assert ms.underpowered_kinds, "6쌍은 선언 목표 10쌍에 미달이다"
        assert "결론이다" in ms.heterogeneity_verdict, (
            "목표 미달 상태의 판정을 중간 경과로 표시하지 않았다 - "
            "여기서 멈추면 optional stopping 이 된다"
        )

    def test_a_fully_powered_verdict_has_no_caveat(self) -> None:
        n = TARGET_PAIRS_PER_KIND
        outcomes = [
            _outcome(f"hi{i}", [Outcome.FALSE_POSITIVE] * 10) for i in range(n)
        ] + [_outcome(f"lo{i}", [Outcome.UNDECIDABLE] * 10) for i in range(n)]
        samples = _samples(
            {f"hi{i}": "kind_hi" for i in range(n)}
            | {f"lo{i}": "kind_lo" for i in range(n)}
        )
        ms = mix_sensitivity(outcomes, samples, GRADER)

        assert not ms.underpowered_kinds
        assert "실재한다" in ms.heterogeneity_verdict
        assert "결론이다" not in ms.heterogeneity_verdict


class TestBothRatesAreReported:
    """지적 단위와 샘플 단위를 둘 다 낸다 - 지적은 독립 시행이 아니다."""

    def test_one_decoy_emitting_many_does_not_look_like_many_decoys(self) -> None:
        outcomes = [
            _outcome("loud", [Outcome.FALSE_POSITIVE] * 8),
            _outcome("quiet", [Outcome.UNDECIDABLE]),
        ]
        samples = _samples({"loud": "same", "quiet": "same"})
        (kind,) = mix_sensitivity(outcomes, samples, GRADER).kinds

        assert kind.rate.successes == 8
        assert kind.rate.total == 9
        # 샘플 단위로는 2건 중 1건만 물렸다 - 8/9 와 크게 어긋난다
        assert (kind.sample_rate.successes, kind.sample_rate.total) == (1, 2)
        assert kind.samples == 2


class TestTheTwoAxesAreOrthogonal:
    """🔴 한 축만 고르게 채워도 다른 축이 쏠릴 수 있다 - 둘 다 잰다."""

    def test_shape_axis_reads_a_different_field(self) -> None:
        samples = _samples({"a": "trap_x", "b": "trap_x"}, shapes={"a": "local", "b": "module"})
        outcomes = [
            _outcome("a", [Outcome.UNDECIDABLE]),
            _outcome("b", [Outcome.FALSE_POSITIVE]),
        ]
        by_trap = mix_sensitivity(outcomes, samples, GRADER, Axis.TRAP)
        by_shape = mix_sensitivity(outcomes, samples, GRADER, Axis.SHAPE)

        assert len(by_trap.kinds) == 1, "미끼 분류로는 한 덩어리다"
        assert len(by_shape.kinds) == 2, "가드 위치로는 갈린다 - 축이 직교한다"
        assert by_trap.reachable == (0.5, 0.5)
        assert by_shape.reachable == (0.0, 1.0)

    def test_axis_label_appears_in_the_report(self) -> None:
        samples = _samples({"a": "k"}, shapes={"a": "local"})
        outcomes = [_outcome("a", [Outcome.FALSE_POSITIVE])]
        assert "가드 위치" in mix_sensitivity(
            outcomes, samples, GRADER, Axis.SHAPE
        ).render()

    def test_shipped_corpus_carries_both(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        negatives = [s for s in shipped_samples if s.is_proven_safe]
        assert negatives
        for s in negatives:
            assert s.safety is not None
            assert s.safety.category, f"{s.sample_id}: 미끼 분류가 없다"
            assert s.safety.shape, f"{s.sample_id}: 가드 위치가 없다 (도출 실패)"


class TestPositivesAreExcluded:
    """🔴 양성(twin)의 지적을 섞으면 FP율이 아니라 다른 숫자가 된다."""

    def test_twin_findings_do_not_enter(self) -> None:
        outcomes = [
            _outcome("d", [Outcome.UNDECIDABLE]),
            _outcome("d#twin", [Outcome.FALSE_POSITIVE] * 5, safe=False),
        ]
        ms = mix_sensitivity(outcomes, _samples({"d": "k"}), GRADER)
        assert ms.observed.total == 1


def _samples(
    kinds: dict[str, str], shapes: dict[str, str] | None = None
) -> list[LabeledSample]:
    shapes = shapes or {}
    return [
        LabeledSample(
            target=ReviewTarget(
                target_id=sid, files=(SourceFile(path="decoy.py", content="x = 1\n"),)
            ),
            stratum=Stratum.DECOY,
            safety=SafetyRationale(
                claim="c",
                justification="j",
                category=kind,
                shape=shapes.get(sid),
            ),
            paired_with=f"{sid}#twin",
        )
        for sid, kind in kinds.items()
    ]
