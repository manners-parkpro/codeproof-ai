"""다회 실행의 짝 채점 - 합집합 · 단일 실행 기대값 · k-임계는 **다른 숫자**다 (F3 · F6).

실제 코퍼스 짝(D005)으로 2회 실행을 흉내 낸다. twin 은 두 번 다 결함을 잡고,
decoy 는 **두 번째 실행에서만** 안전한 쪽을 잘못 지적한다 - 드물게 튀는 지적이다.

    합집합       decoy 도 「지적함」 → P-V
    실행 0       P-C · 실행 1 P-V → 단일 실행 기대값 50%
    k≥2         튄 지적(1/2)은 빠진다 → P-C
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import PRESENTED_FILENAME, load_decoy_samples
from codeproof_ai.eval.multirun import at_least, expectation, thresholds, total_runs
from codeproof_ai.eval.pairing import PairVerdict, score_pairs
from codeproof_ai.eval.runner import ReviewerRun, run_reviewer
from codeproof_ai.reviewers.imported import ImportedReviewer

if TYPE_CHECKING:
    from codeproof_ai.eval.grading.base import Grader
    from codeproof_ai.eval.runner import SampleOutcome

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"
D005 = "D005-half-open-contract"  # twin 결함 L9 · decoy 근거가 덮는 구간 L7-15
G = "provable_safety"


def _llm(start: int, end: int) -> dict[str, object]:
    return {
        "file": PRESENTED_FILENAME, "line_start": start, "line_end": end,
        "category": "correctness", "severity": "error", "quoted_code": f"L{start}-{end}",
        "message": "m", "failure_mode": "f",
    }


def _run(tmp_path: Path, runs: dict[str, list[list[dict[str, object]]]]) -> ReviewerRun:
    samples = [s for s in load_decoy_samples(DECOYS) if s.sample_id in runs]
    root = tmp_path / "out"
    root.mkdir()
    for sid, per_run in runs.items():
        for i, fs in enumerate(per_run):
            (root / f"{sid}.{i}.json").write_text(json.dumps({"findings": fs}), encoding="utf-8")
    n = len(next(iter(runs.values())))
    reviewer = ImportedReviewer(
        root, name="agent", identity="t", kind=ReviewerKind.AGENT, fmt="native"
    )
    graders: list[Grader] = [ProvableSafetyGrader(), InjectedDefectGrader()]
    return run_reviewer(reviewer, samples, graders, sample_n=n, harness_sha="test")


@pytest.fixture
def flaky(tmp_path: Path) -> ReviewerRun:
    return _run(tmp_path, {
        D005: [[], [_llm(8, 9)]],                 # 두 번째 실행에서만 튄다
        f"{D005}#twin": [[_llm(9, 9)], [_llm(9, 9)]],
    })


class TestViewsAreDifferentNumbers:
    def test_union_counts_a_one_off_finding(self, flaky: ReviewerRun) -> None:
        (pair,) = score_pairs(flaky.outcomes, G)
        assert pair.verdict is PairVerdict.OVER_FLAG

    def test_each_run_is_what_a_developer_sees(self, flaky: ReviewerRun) -> None:
        # 계약의 두 번째 줄 - 같은 데이터가 실행 0 에서는 구별 성공이다.
        (first,) = score_pairs(flaky.outcomes, G, run=0)
        (second,) = score_pairs(flaky.outcomes, G, run=1)
        assert (first.verdict, second.verdict) == (PairVerdict.CORRECT, PairVerdict.OVER_FLAG)

    def test_single_run_expectation_averages_the_runs(self, flaky: ReviewerRun) -> None:
        e = expectation(flaky.outcomes, G)
        assert e.per_run == (1, 0)
        assert e.point == pytest.approx(0.5)

    def test_threshold_drops_the_one_off(self, flaky: ReviewerRun) -> None:
        assert at_least(flaky.outcomes, G, 2).successes == 1
        assert at_least(flaky.outcomes, G, 1).successes == 0

    def test_views_are_exclusive(self, flaky: ReviewerRun) -> None:
        with pytest.raises(ValueError, match="하나만"):
            score_pairs(flaky.outcomes, G, run=0, at_least=2)


class TestExpectationInterval:
    def test_deterministic(self, flaky: ReviewerRun) -> None:
        # 🔴 생성물에 실리는 값이다 - 돌릴 때마다 달라지면 「최신인가」를 물을 수 없다.
        assert expectation(flaky.outcomes, G) == expectation(flaky.outcomes, G)

    def test_interval_contains_the_point(self, flaky: ReviewerRun) -> None:
        e = expectation(flaky.outcomes, G)
        assert e.interval is not None
        assert e.point is not None
        assert e.interval[0] <= e.point <= e.interval[1]

    def test_uneven_runs_are_refused(self, tmp_path: Path) -> None:
        # 모자란 실행은 「지적 0건」으로 읽힌다 - 그런 짝을 받으면 거부한다.
        run = _run(tmp_path, {D005: [[], []], f"{D005}#twin": [[_llm(9, 9)], [_llm(9, 9)]]})
        twin = next(o for o in run.outcomes if o.sample_id.endswith("#twin"))
        with pytest.raises(ValueError, match="실행 횟수가 다르다"):
            total_runs([run.outcomes[0], _with_runs(twin, 3)])


def _with_runs(outcome: SampleOutcome, runs: int) -> SampleOutcome:
    obs = dataclasses.replace(outcome.observations, total_runs=runs)
    return dataclasses.replace(outcome, observations=obs)


class TestThresholds:
    def test_one_run_has_one_view(self) -> None:
        assert thresholds(1) == (("1회", 1),)

    def test_eight_runs(self) -> None:
        assert thresholds(8) == (("k≥1 (합집합)", 1), ("k≥5 (과반)", 5), ("k=8 (만장일치)", 8))

    def test_two_runs_majority_is_unanimity(self) -> None:
        assert thresholds(2) == (("k≥1 (합집합)", 1), ("k=2 (만장일치)", 2))
