"""다회 실행 관측 모델.

🔴 여기서 가장 중요한 건 **"단일 실행 기대값"과 "k-임계"가 다른 숫자임을
   구조적으로 보장**하는 것이다. 둘을 섞는 게 이 분야 숫자가 과대포장되는
   흔한 경로이고, 타입이 그걸 막아야 한다.
"""

from __future__ import annotations

import pytest

from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.observation import (
    FingerprintGrouper,
    LocationGrouper,
    ObservationSet,
    ObservedFinding,
    group_runs,
)


def _f(rule: str, line: int = 10, symbol: str = "mod.fn", snippet: str = "x = 1") -> Finding:
    return Finding(
        source="claude",
        rule_id=rule,
        message=f"{rule} at {line}",
        location=Location(
            path="a.py", span=Span(start=Position(line=line, column=0)), symbol=symbol
        ),
        category=Category.CORRECTNESS,
        severity=Severity.WARNING,
        quoted_code=snippet,
    )


class TestGrouping:
    def test_same_finding_across_runs_is_one_observation(self) -> None:
        obs = group_runs("t", [[_f("null-deref")], [_f("null-deref")], [_f("null-deref")]])
        assert len(obs.observed) == 1
        assert obs.observed[0].occurrences == 3
        assert obs.observed[0].is_unanimous

    def test_distinct_findings_stay_separate(self) -> None:
        obs = group_runs("t", [[_f("null-deref"), _f("sqli", symbol="mod.q")]])
        assert len(obs.observed) == 2

    def test_records_which_runs_not_just_how_many(self) -> None:
        """🔴 집합으로 들어야 임의의 슬라이스가 사후 유도된다."""
        obs = group_runs("t", [[_f("a")], [], [_f("a")], []])
        assert obs.observed[0].runs == frozenset({0, 2})

    def test_line_drift_does_not_split_an_observation(self) -> None:
        """fingerprint 는 라인을 안 본다 - 위쪽이 밀려도 같은 지적이다."""
        obs = group_runs("t", [[_f("a", line=10)], [_f("a", line=40)]])
        assert len(obs.observed) == 1

    def test_variants_preserve_original_wording(self) -> None:
        obs = group_runs("t", [[_f("a")], [_f("a")]])
        assert len(obs.observed[0].variants) == 2

    def test_rate_is_occurrence_not_confidence(self) -> None:
        obs = group_runs("t", [[_f("a")], [], [], []])
        assert obs.observed[0].rate == 0.25


class TestGrouperIsAMeasurementChoice:
    """🔴 정책이 바뀌면 출현율이 바뀐다 - 그래서 매니페스트에 기록한다."""

    def test_different_groupers_give_different_counts(self) -> None:
        runs = [[_f("a", line=10, snippet="x = 1")], [_f("a", line=11, snippet="y = 2")]]

        strict = group_runs("t", runs, FingerprintGrouper())
        loose = group_runs("t", runs, LocationGrouper(bucket=5))

        assert len(strict.observed) == 2, "인용문이 다르면 fingerprint 는 나눈다"
        assert len(loose.observed) == 1, "location 정책은 같은 심볼이면 묶는다"
        assert strict.grouper != loose.grouper

    def test_grouper_name_is_recorded(self) -> None:
        obs = group_runs("t", [[_f("a")]], LocationGrouper(bucket=7))
        assert "bucket=7" in obs.grouper

    def test_rejects_nonsense_bucket(self) -> None:
        with pytest.raises(ValueError, match="1 이상"):
            LocationGrouper(bucket=0)


class TestTwoNumbersAreDistinct:
    """🔴 단일 실행 기대값 ≠ k-임계. 섞으면 안 된다."""

    def _mixed(self) -> ObservationSet:
        # 실행 0: a, b   / 실행 1: a   / 실행 2: a, c   / 실행 3: a
        return group_runs(
            "t",
            [
                [_f("a"), _f("b", symbol="m.b")],
                [_f("a")],
                [_f("a"), _f("c", symbol="m.c")],
                [_f("a")],
            ],
        )

    def test_union_overstates_a_single_run(self) -> None:
        obs = self._mixed()
        union = len(obs.observed)
        per_run = [len(obs.in_run(i)) for i in range(obs.total_runs)]
        assert union == 3
        assert per_run == [2, 1, 2, 1]
        assert union > max(per_run), (
            "합집합이 어떤 단일 실행보다 크다 - 이걸 '개발자가 보는 것' 이라고 "
            "부르면 지적 수를 부풀리게 된다"
        )

    def test_mean_per_run_is_not_the_union_size(self) -> None:
        obs = self._mixed()
        assert obs.mean_findings_per_run == 1.5
        assert obs.mean_findings_per_run != len(obs.observed)

    def test_threshold_filters_flaky_findings(self) -> None:
        obs = self._mixed()
        assert len(obs.at_least(1)) == 3
        assert len(obs.at_least(2)) == 1
        assert len(obs.at_least(4)) == 1
        assert obs.at_least(4)[0].finding.rule_id == "a"

    def test_unanimous_is_a_strict_subset(self) -> None:
        obs = self._mixed()
        assert len(obs.unanimous) == 1
        assert len(obs.unanimous) < len(obs.observed)


class TestSystematicVersusFlaky:
    """같은 오답 N번과 서로 다른 오답 N개는 구별되어야 한다."""

    def test_systematic_and_flaky_differ_in_structure(self) -> None:
        systematic = group_runs("t", [[_f("a")] for _ in range(4)])
        flaky = group_runs(
            "t", [[_f(r, symbol=f"m.{r}")] for r in ("a", "b", "c", "d")]
        )

        # 합집합만 보면 구별 안 되던 것이, 구조로는 갈린다.
        assert systematic.mean_findings_per_run == flaky.mean_findings_per_run
        assert len(systematic.observed) == 1
        assert len(flaky.observed) == 4
        assert len(systematic.unanimous) == 1
        assert len(flaky.unanimous) == 0


class TestValidation:
    def test_rejects_observation_with_no_runs(self) -> None:
        with pytest.raises(ValueError, match="한 번도 등장하지"):
            ObservedFinding(finding=_f("a"), runs=frozenset(), total_runs=3)

    def test_rejects_run_index_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="범위를 벗어난다"):
            ObservedFinding(finding=_f("a"), runs=frozenset({5}), total_runs=3)

    def test_rejects_empty_run_list(self) -> None:
        with pytest.raises(ValueError, match="실행이 하나도 없다"):
            group_runs("t", [])

    def test_a_run_with_no_findings_is_valid(self) -> None:
        obs = group_runs("t", [[_f("a")], []])
        assert obs.total_runs == 2
        assert obs.in_run(1) == ()
