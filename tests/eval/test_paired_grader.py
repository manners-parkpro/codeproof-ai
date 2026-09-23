"""짝 기반 채점자.

🔴 이 채점자의 존재 이유: `score_pairs()` 는 **사후 요약**이라
   per-finding Precision 을 고치지 못한다.

[실측] `D002#twin` 의 S602 는 안전한 쪽에도 똑같이 나오는데
   InjectedDefectGrader 는 결함 위치와 겹치므로 TP 를 준다.
   짝 요약은 그 쌍을 P-V 로 표시하지만 Precision 숫자는 오염된 채다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.conftest import AnalyzedCorpus

from pathlib import Path

import pytest

from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.observation import group_runs
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.grading.base import Grader, Outcome, UnboundGraderError
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.paired import PairedFixGrader
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.eval.sample import (
    Defect,
    DefectOrigin,
    LabeledSample,
    SafetyRationale,
    Stratum,
)

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


def _finding(rule: str, path: str, line: int, symbol: str = "fn") -> Finding:
    return Finding(
        source="ruff",
        rule_id=rule,
        message="m",
        location=Location(path=path, span=Span(Position(line, 0)), symbol=symbol),
        category=Category.SECURITY,
        severity=Severity.ERROR,
        quoted_code=f"line{line}",
    )


def _positive() -> LabeledSample:
    return LabeledSample(
        target=ReviewTarget(
            target_id="p#twin",
            files=(SourceFile("twin.py", "\n".join(f"L{i}" for i in range(20))),),
        ),
        stratum=Stratum.DECOY,
        defects=(
            Defect(
                location=Location(
                    path="twin.py", span=Span(Position(5, 0), Position(10, 0))
                ),
                origin=DefectOrigin.INJECTED,
                description="가드 제거",
            ),
        ),
        paired_with="p",
    )


def _negative() -> LabeledSample:
    return LabeledSample(
        target=ReviewTarget(
            target_id="p",
            files=(SourceFile("decoy.py", "\n".join(f"L{i}" for i in range(20))),),
        ),
        stratum=Stratum.DECOY,
        safety=SafetyRationale(
            claim="안전하다",
            justification="호출부가 보장하기 때문에 안전하고 그 근거는 명확하다 " * 2,
            covered_path="decoy.py",
            covered_lines=(5, 10),
        ),
        paired_with="p#twin",
    )


def _judge(
    sample: LabeledSample,
    findings: list[Finding],
    counterpart: list[Finding],
    slack: int = 0,
) -> Outcome:
    g = PairedFixGrader(line_slack=slack)
    g.bind_run({sample.paired_with or "": counterpart})
    obs = group_runs(sample.sample_id, [findings])
    out = g.judge(sample, obs.observed)
    assert len(out) == 1
    return out[0].outcome


class TestDiscrimination:
    """🔴 핵심 — 짝에도 있으면 탐지의 증거가 아니다."""

    def test_unique_to_the_twin_is_a_true_positive(self) -> None:
        got = _judge(_positive(), [_finding("S602", "twin.py", 7)], counterpart=[])
        assert got is Outcome.TRUE_POSITIVE

    def test_present_in_both_is_not_detection(self) -> None:
        got = _judge(
            _positive(),
            [_finding("S602", "twin.py", 7)],
            counterpart=[_finding("S602", "decoy.py", 7)],
        )
        assert got is Outcome.UNDECIDABLE

    def test_not_detection_is_not_called_wrong(self) -> None:
        """⚠ 변별력 없음을 FP 로 접으면 우리가 비판하는 그 오류가 된다."""
        g = PairedFixGrader()
        g.bind_run({"p": [_finding("S602", "decoy.py", 7)]})
        obs = group_runs("p#twin", [[_finding("S602", "twin.py", 7)]])
        j = g.judge(_positive(), obs.observed)[0]
        assert j.outcome is not Outcome.FALSE_POSITIVE
        assert "증거가 아니다" in j.rationale
        assert j.matched_defect is not None, "결함과는 겹친다는 사실은 남긴다"

    def test_different_rule_in_the_pair_still_counts(self) -> None:
        """다른 룰이면 구별한 것이다."""
        got = _judge(
            _positive(),
            [_finding("S602", "twin.py", 7)],
            counterpart=[_finding("E501", "decoy.py", 7)],
        )
        assert got is Outcome.TRUE_POSITIVE

    def test_different_symbol_in_the_pair_still_counts(self) -> None:
        got = _judge(
            _positive(),
            [_finding("S602", "twin.py", 7, symbol="a")],
            counterpart=[_finding("S602", "decoy.py", 7, symbol="b")],
        )
        assert got is Outcome.TRUE_POSITIVE


class TestOutsideTheDefect:
    def test_finding_away_from_the_defect_is_undecidable(self) -> None:
        got = _judge(_positive(), [_finding("X", "twin.py", 18)], counterpart=[])
        assert got is Outcome.UNDECIDABLE

    def test_slack_widens_the_defect_window(self) -> None:
        f = [_finding("X", "twin.py", 12)]
        assert _judge(_positive(), f, [], slack=0) is Outcome.UNDECIDABLE
        assert _judge(_positive(), f, [], slack=3) is Outcome.TRUE_POSITIVE


class TestNegativeSide:
    def test_any_finding_on_proven_safe_code_is_a_false_positive(self) -> None:
        got = _judge(_negative(), [_finding("S602", "decoy.py", 7)], counterpart=[])
        assert got is Outcome.FALSE_POSITIVE

    def test_pair_presence_does_not_excuse_it(self) -> None:
        got = _judge(
            _negative(),
            [_finding("S602", "decoy.py", 7)],
            counterpart=[_finding("S602", "twin.py", 7)],
        )
        assert got is Outcome.FALSE_POSITIVE


class TestConfiguration:
    def test_rejects_negative_slack(self) -> None:
        with pytest.raises(ValueError, match="0 이상"):
            PairedFixGrader(line_slack=-1)

    def test_slack_is_in_the_signature(self) -> None:
        a = PairedFixGrader(line_slack=0).config_signature()
        b = PairedFixGrader(line_slack=3).config_signature()
        assert a != b

    def test_does_not_use_an_llm_judge(self) -> None:
        assert PairedFixGrader().uses_llm_judge is False

    def test_without_bind_run_it_refuses_to_grade(self) -> None:
        """🔴 bind_run 없이는 **채점하지 않는다**.

        전에 이 테스트는 "degrade 하되 죽지 않는다" 를 정답으로 적어 두었다.
        그게 버그를 고정하고 있었다 - 짝 정보가 없으면 「짝에 지적이 없다」로
        읽혀 전부 TP 가 되는데, 그건 틀린 숫자가 아니라 **틀렸다는 걸 알 수 없는
        숫자**다. run_analyzer 경로가 실제로 그렇게 채점하고 있었다.
        """
        g = PairedFixGrader()
        obs = group_runs("p#twin", [[_finding("S602", "twin.py", 7)]])
        with pytest.raises(UnboundGraderError, match="bind_run"):
            g.judge(_positive(), obs.observed)


class TestRunnerBindsTheContext:
    """🔴 runner 가 리뷰와 채점을 분리하지 않으면 짝 정보가 없다."""

    def test_bind_run_is_called_before_grading(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        g = PairedFixGrader()
        run_reviewer(analyzed("ruff"), shipped_samples, [g])
        assert g._by_sample, "runner 가 bind_run 을 부르지 않았다"
        assert len(g._by_sample) == len(shipped_samples)


class TestAgainstShippedCorpus:
    """🔴 실측 회귀 - 다른 채점자와 실제로 답이 갈리는지."""

    def test_diverges_from_injected_on_d002(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        graders: list[Grader] = [InjectedDefectGrader(), PairedFixGrader()]
        run = run_reviewer(
            analyzed("ruff"), shipped_samples, graders
        )
        twin = next(
            o for o in run.outcomes
            if o.sample_id == "D002-shell-true-constant-command#twin"
        )
        injected = {j.outcome for j in twin.judgments["injected_defect"]}
        paired = {j.outcome for j in twin.judgments["paired_fix"]}

        assert Outcome.TRUE_POSITIVE in injected, "픽스처가 바뀌었다"
        assert Outcome.TRUE_POSITIVE not in paired, (
            "짝 채점자가 변별력 없는 지적을 TP 로 인정했다 - 존재 이유가 사라졌다"
        )

    def test_it_is_the_strictest_definition(
        self, analyzed: AnalyzedCorpus, shipped_samples: list[LabeledSample]
    ) -> None:
        """TP 수가 InjectedDefectGrader 보다 많을 수 없다."""
        graders: list[Grader] = [InjectedDefectGrader(), PairedFixGrader()]
        run = run_reviewer(
            analyzed("ruff", ("ALL",)),
            shipped_samples,
            graders,
        )
        counts = {
            name: sum(
                1
                for o in run.outcomes
                for j in o.judgments[name]
                if j.outcome is Outcome.TRUE_POSITIVE
            )
            for name in ("injected_defect", "paired_fix")
        }
        assert counts["paired_fix"] <= counts["injected_defect"], counts
