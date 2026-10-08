"""교차 확인 채점자의 위치 매칭 - 참조 쪽도 보고 범위로 맞춘다 (A2a).

🔴 확인자(verify/)와 채점자(eval/)가 **같은 함수**(`Span.near`)를 쓴다. 한 곳만 범위로 보면
   같은 두 지적이 곳마다 다른 자리에 있게 된다 (F4a 와 같은 교훈).
"""

from __future__ import annotations

from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.observation import ObservedFinding
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.grading.corroboration import StaticCorroborationGrader
from codeproof_ai.eval.sample import LabeledSample, Stratum


def _finding(source: str, start: int, end: int | None = None) -> Finding:
    span = Span(Position(start, 0), Position(end, 0) if end is not None else None)
    return Finding(
        source=source, rule_id="x", message="m", location=Location(path="m.py", span=span),
        category=Category.SECURITY, severity=Severity.WARNING,
    )


def _judge(observed: Finding, reference: Finding) -> Outcome:
    sample = LabeledSample(
        target=ReviewTarget(target_id="S1", files=(SourceFile("m.py", "x\n" * 20),)),
        stratum=Stratum.UNLABELED,
    )
    grader = StaticCorroborationGrader(reference={"S1": [reference]}, reference_name="ref")
    seen = ObservedFinding(
        finding=observed, runs=frozenset({0}), total_runs=1, variants=(observed,),
    )
    return grader.judge(sample, [seen])[0].outcome


class TestReferenceSpan:
    def test_a_wide_reference_corroborates_a_line_inside_it(self) -> None:
        """참조 L4-8 · 관측 L8 - 시작 줄(4)만 보면 slack 2 로는 닿지 않아 판정 불가였다."""
        assert _judge(_finding("ruff", 8), _finding("claude", 4, 8)) is Outcome.TRUE_POSITIVE

    def test_the_match_is_the_same_in_both_directions(self) -> None:
        wide, line = _finding("claude", 4, 8), _finding("ruff", 8)
        assert _judge(line, wide) is _judge(wide, line) is Outcome.TRUE_POSITIVE

    def test_a_reference_far_away_still_does_not_corroborate(self) -> None:
        """대조군 - 범위로 맞춘다고 아무 데나 닿는 것은 아니다."""
        assert _judge(_finding("ruff", 18), _finding("claude", 4, 8)) is Outcome.UNDECIDABLE
