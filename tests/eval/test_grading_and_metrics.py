"""채점자와 지표.

🔴 핵심은 **판정 불가를 FP 로 접지 않는다** 는 것이다.
   기존 문헌이 정확히 그 지점에서 틀렸다.
"""

from __future__ import annotations

import math

import pytest

from codeproof_ai.analysis.python.ruff import RuffAnalyzer
from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.observation import ObservedFinding, group_runs
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.grading.base import Judgment, Outcome
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.metrics import Proportion, credibility_warning, summarize
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.eval.sample import (
    Defect,
    DefectOrigin,
    LabeledSample,
    SafetyRationale,
    Stratum,
)
from codeproof_ai.reviewers.wrap import AnalyzerReviewer

SRC = "\n".join(f"line_{i}" for i in range(1, 41)) + "\n"


def _obs(line: int, rule: str = "S602") -> tuple[ObservedFinding, ...]:
    f = Finding(
        source="ruff",
        rule_id=rule,
        message="m",
        location=Location(path="decoy.py", span=Span(Position(line, 0)), symbol="fn"),
        category=Category.SECURITY,
        severity=Severity.ERROR,
        quoted_code=f"line_{line}",
    )
    return group_runs("t", [[f]]).observed


def _safe_sample(covered: tuple[int, int] = (5, 13)) -> LabeledSample:
    return LabeledSample(
        target=ReviewTarget(target_id="d1", files=(SourceFile("decoy.py", SRC),)),
        stratum=Stratum.DECOY,
        safety=SafetyRationale(
            claim="9행은 안전하다",
            justification="호출부가 보장하기 때문에 안전하다 " * 3,
            covered_path="decoy.py",
            covered_lines=covered,
        ),
        paired_with="d1#twin",
    )


def _buggy_sample(defect_lines: tuple[int, int] = (5, 10)) -> LabeledSample:
    return LabeledSample(
        target=ReviewTarget(target_id="d1#twin", files=(SourceFile("twin.py", SRC),)),
        stratum=Stratum.DECOY,
        defects=(
            Defect(
                location=Location(
                    path="twin.py",
                    span=Span(Position(defect_lines[0], 0), Position(defect_lines[1], 0)),
                ),
                origin=DefectOrigin.INJECTED,
                description="가드 제거",
            ),
        ),
        paired_with="d1",
    )


class TestProvableSafetyGrader:
    def test_finding_inside_covered_region_is_false_positive(self) -> None:
        js = ProvableSafetyGrader().judge(_safe_sample(), _obs(9))
        assert js[0].outcome is Outcome.FALSE_POSITIVE
        assert "서면 근거" in js[0].rationale

    def test_finding_outside_covered_region_is_undecidable(self) -> None:
        """🔴 이게 핵심이다. 전부 FP 로 접으면 우리가 비판한 그 짓이 된다."""
        js = ProvableSafetyGrader().judge(_safe_sample(), _obs(30))
        # FP 가 아니라 UNDECIDABLE 이어야 한다 - 전부 FP 로 접으면
        # 판정 불가를 오답으로 채점하는 것이고, 그게 기존 문헌의 오류다.
        assert js[0].outcome is Outcome.UNDECIDABLE

    def test_slack_widens_the_covered_region(self) -> None:
        """slack 도 측정 손잡이다 - 늘리면 FP 가 늘어난다."""
        strict = ProvableSafetyGrader(overlap_slack=0).judge(_safe_sample(), _obs(15))
        loose = ProvableSafetyGrader(overlap_slack=5).judge(_safe_sample(), _obs(15))
        assert strict[0].outcome is Outcome.UNDECIDABLE
        assert loose[0].outcome is Outcome.FALSE_POSITIVE

    def test_slack_is_in_the_signature(self) -> None:
        a = ProvableSafetyGrader(overlap_slack=0).config_signature()
        b = ProvableSafetyGrader(overlap_slack=3).config_signature()
        assert a != b

    def test_rejects_negative_slack(self) -> None:
        with pytest.raises(ValueError, match="0 이상"):
            ProvableSafetyGrader(overlap_slack=-1)

    def test_finding_on_the_defect_is_true_positive(self) -> None:
        f = Finding(
            source="ruff",
            rule_id="S602",
            message="m",
            location=Location(path="twin.py", span=Span(Position(7, 0))),
            category=Category.SECURITY,
            severity=Severity.ERROR,
            quoted_code="line_7",
        )
        js = ProvableSafetyGrader().judge(_buggy_sample(), group_runs("t", [[f]]).observed)
        assert js[0].outcome is Outcome.TRUE_POSITIVE

    def test_unlabeled_location_on_a_buggy_sample_is_undecidable(self) -> None:
        f = Finding(
            source="ruff",
            rule_id="E501",
            message="m",
            location=Location(path="twin.py", span=Span(Position(35, 0))),
            category=Category.STYLE,
            severity=Severity.WARNING,
            quoted_code="line_35",
        )
        js = ProvableSafetyGrader().judge(_buggy_sample(), group_runs("t", [[f]]).observed)
        assert js[0].outcome is Outcome.UNDECIDABLE

    def test_does_not_use_an_llm_judge(self) -> None:
        """E3 - 자기선호 편향 때문에 v1 채점자는 전부 비-LLM 이다."""
        assert ProvableSafetyGrader().uses_llm_judge is False


class TestProportion:
    def test_wilson_interval_stays_inside_zero_one(self) -> None:
        for s, n in ((0, 5), (5, 5), (1, 3), (0, 1)):
            lo, hi = Proportion(s, n).interval  # type: ignore[misc]
            assert 0.0 <= lo <= hi <= 1.0

    def test_wilson_is_not_degenerate_at_the_extremes(self) -> None:
        """Wald 근사는 0/n 에서 폭 0 을 낸다 - Wilson 은 그러지 않는다."""
        _lo, hi = Proportion(0, 5).interval  # type: ignore[misc]
        assert hi > 0.0, "0/5 의 상한이 0 이면 Wald 를 쓴 것이다"

    def test_half_width_shrinks_with_sample_size(self) -> None:
        small = Proportion(3, 10).half_width
        large = Proportion(30, 100).half_width
        assert small is not None and large is not None
        assert large < small

    def test_matches_known_wilson_value(self) -> None:
        """p=0.3, n=150 에서 반폭 ≈ 7.3pp (설계 문서의 표)."""
        hw = Proportion(45, 150).half_width
        assert hw is not None
        assert math.isclose(hw, 0.073, abs_tol=0.004)

    def test_empty_sample_is_not_a_number(self) -> None:
        p = Proportion(0, 0)
        assert p.point is None
        assert p.interval is None
        assert "n/a" in p.render()


class TestCredibilityWarning:
    def test_warns_below_one_hundred_negatives(self) -> None:
        assert credibility_warning(2) is not None
        assert credibility_warning(99) is not None

    def test_silent_at_or_above_one_hundred(self) -> None:
        assert credibility_warning(100) is None
        assert credibility_warning(150) is None


class TestSummarize:
    def test_undecidable_is_excluded_from_precision(self) -> None:
        """🔴 판정 불가를 분모에 넣으면 Precision 이 조용히 낮아진다."""
        js = [
            Judgment("k1", Outcome.TRUE_POSITIVE, "g"),
            Judgment("k2", Outcome.FALSE_POSITIVE, "g"),
            *[Judgment(f"k{i}", Outcome.UNDECIDABLE, "g") for i in range(3, 13)],
        ]
        r = summarize("g", "d", "s", js)
        assert r.precision.total == 2, "판정 불가가 분모에 섞였다"
        assert r.precision.point == 0.5
        assert r.undecidable_rate.point == 10 / 12


class TestEndToEnd:
    def test_runner_separates_strata(self) -> None:
        """🔴 층을 섞어 집계하지 않는다 (E2)."""
        samples = [_safe_sample(), _buggy_sample()]
        run = run_reviewer(
AnalyzerReviewer(RuffAnalyzer(select=("F",))), samples, [ProvableSafetyGrader()])
        strata = {r.stratum for r in run.results}
        assert strata == {"증명된 음성", "양성(twin)"}

    def test_manifest_records_the_knobs(self) -> None:
        run = run_reviewer(
AnalyzerReviewer(RuffAnalyzer(select=("F", "E"))), [_safe_sample()], [ProvableSafetyGrader()]
        )
        block = run.manifest.disclosure_block()
        assert "F+E" in block, "룰 선택이 공개 블록에 없다"
        assert "fingerprint" in block, "그룹핑 정책이 공개 블록에 없다"
        assert "ruff" in run.manifest.model_id

    def test_corpus_hash_changes_with_content(self) -> None:
        a = run_reviewer(
AnalyzerReviewer(RuffAnalyzer(select=("F",))), [_safe_sample()], [])
        b = run_reviewer(
AnalyzerReviewer(RuffAnalyzer(select=("F",))), [_buggy_sample()], [])
        assert a.manifest.corpus_hash != b.manifest.corpus_hash
