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
from codeproof_ai.eval.mix import mix_sensitivity
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


class TestPositivesAreExcluded:
    """🔴 양성(twin)의 지적을 섞으면 FP율이 아니라 다른 숫자가 된다."""

    def test_twin_findings_do_not_enter(self) -> None:
        outcomes = [
            _outcome("d", [Outcome.UNDECIDABLE]),
            _outcome("d#twin", [Outcome.FALSE_POSITIVE] * 5, safe=False),
        ]
        ms = mix_sensitivity(outcomes, _samples({"d": "k"}), GRADER)
        assert ms.observed.total == 1


def _samples(kinds: dict[str, str]) -> list[LabeledSample]:
    return [
        LabeledSample(
            target=ReviewTarget(
                target_id=sid, files=(SourceFile(path="decoy.py", content="x = 1\n"),)
            ),
            stratum=Stratum.DECOY,
            safety=SafetyRationale(
                claim="c", justification="j", category=kind
            ),
            paired_with=f"{sid}#twin",
        )
        for sid, kind in kinds.items()
    ]
