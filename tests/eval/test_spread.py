"""채점 기준 편차 - 이 프로젝트의 헤드라인.

🔴 핵심 검사는 두 가지다.
   ① 같은 지적이 정의에 따라 다르게 채점되는가 (편차가 실재하는가)
   ② 어휘가 다른 채점자를 편차에 섞지 않는가 (범주 차이를 편차로 오해하지 않는가)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from codeproof_ai.eval.grading.base import Grader, Outcome
from codeproof_ai.eval.grading.corroboration import (
    SelfCorroborationError,
    StaticCorroborationGrader,
)
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.eval.spread import Spread, compute_spread

if TYPE_CHECKING:
    from codeproof_ai.eval.sample import LabeledSample
    from tests.conftest import AnalyzedCorpus


def _graders(analyzed: AnalyzedCorpus) -> list[Grader]:
    """🔴 확인자 지적을 일괄로 미리 계산해 넘긴다 - 채점자는 증거를 받는다."""
    return [
        ProvableSafetyGrader(),
        InjectedDefectGrader(),
        StaticCorroborationGrader(
            reference=analyzed.findings("mypy"),
            reference_name="mypy",
        ),
    ]


def _run(
    analyzed: AnalyzedCorpus,
    samples: list[LabeledSample],
    select: tuple[str, ...],
) -> Spread:
    graders = _graders(analyzed)
    run = run_reviewer(
        analyzed("ruff", select), samples, graders, harness_sha="test"
    )
    return compute_spread(run.outcomes, graders, negatives_only=True)


class TestVerdictVocabulary:
    """🔴 채점자마다 낼 수 있는 판정이 다르다."""

    def test_corroboration_cannot_emit_false_positive(self) -> None:
        """동의가 없는 것은 반증이 아니다 - 이 정의로는 「틀렸다」를 말할 수 없다."""
        g = StaticCorroborationGrader(reference={})
        assert Outcome.FALSE_POSITIVE not in g.emits

    def test_injected_has_no_undecidable(self) -> None:
        """Qodo 정의에는 판정 불가 칸이 없다 - 그래서 FP 가 부풀려진다."""
        assert Outcome.UNDECIDABLE not in InjectedDefectGrader().emits

    def test_safety_has_all_three(self) -> None:
        assert ProvableSafetyGrader().emits == {
            Outcome.TRUE_POSITIVE,
            Outcome.FALSE_POSITIVE,
            Outcome.UNDECIDABLE,
        }


class TestSpreadExcludesIncomparableGraders:
    def test_non_fp_grader_is_excluded_from_range(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        sp = _run(analyzed, shipped_samples, ("ALL",))
        names = {c.grader for c in sp.comparable}
        assert "static_corroboration" not in names, (
            "FP 를 못 내는 채점자의 0 이 편차에 섞였다 - 범주 차이를 편차로 오해한다"
        )
        assert names == {"provable_safety", "injected_defect"}

    def test_all_graders_still_reported(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """제외는 **편차 계산**에서만이다. 표에서는 보여준다."""
        sp = _run(analyzed, shipped_samples, ("ALL",))
        assert len(sp.columns) == 3


class TestSpreadIsReal:
    """🔴 같은 지적, 다른 정의, 다른 숫자."""

    def test_definitions_disagree_on_the_same_findings(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        sp = _run(analyzed, shipped_samples, ("ALL",))
        assert sp.findings > 0

        by_name = {c.grader: c for c in sp.columns}
        safety = by_name["provable_safety"]
        injected = by_name["injected_defect"]

        # 같은 지적 집합을 봤다
        assert safety.total == injected.total == sp.findings

        # 그런데 FP 수가 다르다
        assert injected.false_positive > safety.false_positive, (
            "Qodo 정의가 더 많은 FP 를 내야 한다 - 판정 불가 칸이 없기 때문이다"
        )
        assert safety.undecidable > 0
        assert injected.undecidable == 0

    def test_disagreement_equals_the_undecidable_gap(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """편차의 정체 - 한쪽이 「판정 불가」로 둔 것을 다른 쪽이 「틀렸다」로 센다."""
        sp = _run(analyzed, shipped_samples, ("ALL",))
        by_name = {c.grader: c for c in sp.columns}
        assert sp.disagreement == by_name["provable_safety"].undecidable

    def test_ratio_is_none_when_minimum_is_zero(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """0 으로 나누어 「무한대 배」로 부풀리지 않는다."""
        sp = _run(analyzed, shipped_samples, ("F",))
        assert sp.fp_range[0] == 0, "전제가 깨졌다 - 최솟값이 0 인 설정을 다시 고른다"
        assert sp.fp_ratio is None


class TestSelfCorroborationIsRefused:
    """🔴 Ruff 의 지적을 Ruff 로 확인하면 항상 일치한다 - 측정이 아니라 항등식이다."""

    def test_same_analyzer_as_reference_raises(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        grader = StaticCorroborationGrader(
            reference=analyzed.findings("ruff"),
            reference_name="ruff",
        )
        with pytest.raises(SelfCorroborationError, match="자기 채점"):
            run_reviewer(
                analyzed("ruff"), shipped_samples, [grader], harness_sha="test"
            )

    def test_different_analyzer_is_fine(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        run = run_reviewer(
            analyzed("ruff"), shipped_samples, _graders(analyzed), harness_sha="test"
        )
        assert run.outcomes
