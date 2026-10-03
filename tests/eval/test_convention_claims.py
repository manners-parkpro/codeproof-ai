"""관례 주장은 거짓 경보가 아니다.

🔴 이 프로젝트가 저지를 뻔한 가장 큰 측정 오류다.

`ProvableSafetyGrader` 가 「안전 근거가 덮는 **줄 범위** 안의 지적은 FP」로
채점하고 있었다. 위치 겹침을 「주장이 덮는다」로 읽은 것이다. 그런데 안전
근거는 특정 결함에 대한 것이지 그 줄에 대한 것이 아니다.

[실측] `--select ALL` 로 돌렸을 때 FP 66건 중 **45건이 `D103`**
(docstring 누락)이었다. decoy 함수에 정말 docstring 이 없으니 그 지적은
**옳다.** 맞는 지적을 오답으로 채점한 것이고, 그건 이 프로젝트가 기존 문헌에
대해 비판하는 바로 그 오류(F4)와 같은 종류다.

고친 뒤 FP 66 -> 6. 그리고 그 결과 **앞서 보고한 결론 두 개가 뒤집혔다**:

  · 미끼 시험률 84% -> 10%
  · 「가드가 멀수록 더 문다」(local 18.2% < module 45.2%)가
    (caller 0.0% < local 6.5%) 로 **순서가 반대**가 됐다 -
    함수가 많은 decoy 가 docstring 지적을 더 받았을 뿐이었다

즉 노이즈가 신호처럼 보였다. 그래서 이 테스트를 따로 둔다.
"""

from __future__ import annotations

from codeproof_ai.analysis.registry import create_analyzer
from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.observation import group_runs
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.grading.paired import PairedFixGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.sample import (
    Defect,
    DefectOrigin,
    LabeledSample,
    SafetyRationale,
    Stratum,
)


def _finding(rule: str, line: int, category: Category) -> Finding:
    return Finding(
        source="ruff",
        rule_id=rule,
        message="m",
        location=Location(path="decoy.py", span=Span(Position(line, 0)), symbol="fn"),
        category=category,
        severity=Severity.WARNING,
    )


def _negative() -> LabeledSample:
    return LabeledSample(
        target=ReviewTarget(
            target_id="d",
            files=(SourceFile("decoy.py", "\n".join(f"L{i}" for i in range(20))),),
        ),
        stratum=Stratum.DECOY,
        safety=SafetyRationale(
            claim="이 shell=True 는 안전하다",
            justification="외부 입력이 닿는 경로가 없기 때문이다" * 3,
            covered_path="decoy.py",
            covered_lines=(5, 10),
            category="constant_only_sink",
        ),
        paired_with="d#twin",
    )


def _positive() -> LabeledSample:
    """가드를 지운 twin - 결함 구간은 5-10 행이다 (로더가 만드는 모양과 같다)."""
    return LabeledSample(
        target=ReviewTarget(
            target_id="d#twin",
            files=(SourceFile("decoy.py", "\n".join(f"L{i}" for i in range(20))),),
        ),
        stratum=Stratum.DECOY,
        defects=(
            Defect(
                location=Location(path="decoy.py", span=Span(Position(5, 0), Position(10, 0))),
                origin=DefectOrigin.INJECTED,
                description="가드가 빠져 외부 입력이 셸에 닿는다",
                category="constant_only_sink",
            ),
        ),
        paired_with="d",
    )


class TestCategoryDrawsTheLine:
    def test_style_is_not_a_defect_claim(self) -> None:
        assert Category.STYLE.is_defect_claim is False

    def test_everything_else_is(self) -> None:
        """🔴 `OTHER` 도 결함 주장으로 친다.

        모델 지적은 분류가 비어 올 수 있는데, 그걸 관례로 취급하면
        **모델의 FP 가 조용히 사라진다.** 놓치는 쪽이 세는 쪽보다 나쁘다.
        """
        for c in Category:
            if c is not Category.STYLE:
                assert c.is_defect_claim, f"{c} 가 결함 주장에서 빠졌다"


class TestProvableSafetyIgnoresConventionClaims:
    def test_style_finding_inside_the_range_is_undecidable(self) -> None:
        obs = group_runs("d", [[_finding("D103", 7, Category.STYLE)]])
        (j,) = ProvableSafetyGrader().judge(_negative(), obs.observed)
        assert j.outcome is Outcome.UNDECIDABLE, (
            "docstring 누락을 FP 로 셌다 - 그 지적은 **사실이다**"
        )
        assert "관례 주장" in j.rationale

    def test_defect_finding_inside_the_range_is_still_a_false_positive(self) -> None:
        obs = group_runs("d", [[_finding("S602", 7, Category.SECURITY)]])
        (j,) = ProvableSafetyGrader().judge(_negative(), obs.observed)
        assert j.outcome is Outcome.FALSE_POSITIVE

    def test_defect_finding_outside_the_range_is_undecidable(self) -> None:
        obs = group_runs("d", [[_finding("S602", 18, Category.SECURITY)]])
        (j,) = ProvableSafetyGrader().judge(_negative(), obs.observed)
        assert j.outcome is Outcome.UNDECIDABLE

    def test_style_finding_on_the_twin_defect_is_not_a_detection(self) -> None:
        """🔴 twin 쪽도 같다 - 결함 구간에 우연히 걸린 docstring 지적은 탐지가 아니다.

        [실측 · 60쌍] 이 구분이 없을 때 Ruff ALL 의 「구별 성공」 11/60 이 전부 이것이었다.
        """
        obs = group_runs("d#twin", [[_finding("D103", 7, Category.STYLE)]])
        (j,) = ProvableSafetyGrader().judge(_positive(), obs.observed)
        assert j.outcome is Outcome.UNDECIDABLE, "docstring 누락을 결함 탐지로 셌다"
        assert "관례 주장" in j.rationale

    def test_defect_finding_on_the_twin_defect_is_a_detection(self) -> None:
        obs = group_runs("d#twin", [[_finding("S602", 7, Category.SECURITY)]])
        (j,) = ProvableSafetyGrader().judge(_positive(), obs.observed)
        assert j.outcome is Outcome.TRUE_POSITIVE


class TestPairedFixHasTheSameRule:
    """같은 결함이 두 채점자에 있었다 - 한쪽만 고치면 또 갈린다."""

    def test_style_on_a_negative_is_undecidable(self) -> None:
        g = PairedFixGrader()
        g.bind_run({})
        obs = group_runs("d", [[_finding("D103", 7, Category.STYLE)]])
        (j,) = g.judge(_negative(), obs.observed)
        assert j.outcome is Outcome.UNDECIDABLE

    def test_style_on_a_positive_is_not_a_detection(self) -> None:
        g = PairedFixGrader()
        g.bind_run({})
        obs = group_runs("d#twin", [[_finding("D103", 7, Category.STYLE)]])
        (j,) = g.judge(_positive(), obs.observed)
        assert j.outcome is Outcome.UNDECIDABLE

    def test_defect_on_a_positive_absent_from_the_pair_is_a_detection(self) -> None:
        g = PairedFixGrader()
        g.bind_run({})
        obs = group_runs("d#twin", [[_finding("S602", 7, Category.SECURITY)]])
        (j,) = g.judge(_positive(), obs.observed)
        assert j.outcome is Outcome.TRUE_POSITIVE

    def test_defect_on_a_negative_is_a_false_positive(self) -> None:
        g = PairedFixGrader()
        g.bind_run({})
        obs = group_runs("d", [[_finding("S602", 7, Category.SECURITY)]])
        (j,) = g.judge(_negative(), obs.observed)
        assert j.outcome is Outcome.FALSE_POSITIVE


class TestTheCategoryComesFromTheTool:
    """🔴 접두사로 짐작하지 않는다 (C2).

    `TRY003` 과 `PERF203` 은 접두사로는 maintainability · performance 로
    보이지만 Ruff 는 둘 다 `pedantic` 으로 분류한다. 접두사 추정만 쓰면
    이 둘이 결함 주장으로 남아 FP 를 부풀린다.
    """

    SOURCE = (
        "import subprocess\n"
        "\n"
        "\n"
        "def run_it(cmd):\n"
        "    subprocess.run(cmd, shell=True, check=False)\n"
    )

    @staticmethod
    def _by_rule() -> dict[str, Category]:
        """🔴 private 메서드를 찌르지 않는다 - 실제 분석 결과로 본다."""
        analyzer = create_analyzer("ruff", select=("ALL",))
        target = ReviewTarget(
            target_id="t",
            files=(SourceFile("m.py", TestTheCategoryComesFromTheTool.SOURCE),),
        )
        return {f.rule_id: f.category for f in analyzer.analyze(target)}

    def test_pedantic_rules_come_back_as_convention_claims(self) -> None:
        by_rule = self._by_rule()
        assert "D103" in by_rule, "이 코드가 docstring 룰을 내야 시험이 성립한다"
        convention = {"D103", "ANN001", "ANN201", "INP001", "CPY001", "EM101"}
        for code, cat in by_rule.items():
            if code in convention:
                assert cat is Category.STYLE, f"{code} 가 관례로 안 잡혔다"

    def test_security_rules_stay_defect_claims(self) -> None:
        by_rule = self._by_rule()
        assert "S602" in by_rule, "이 코드가 shell=True 룰을 내야 시험이 성립한다"
        assert by_rule["S602"].is_defect_claim

    def test_the_source_is_recorded_in_the_signature(self) -> None:
        """🔴 introspect 와 접두사 추정은 다른 숫자를 낸다 - 매니페스트에 적는다."""

        assert "cat=" in create_analyzer("ruff").config_signature()
