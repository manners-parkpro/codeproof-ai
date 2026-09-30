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
from codeproof_ai.eval.grading.base import UnboundGraderError
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.paired import PairedFixGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import PRESENTED_FILENAME, load_decoy_samples
from codeproof_ai.eval.multirun import at_least, difference, expectation, thresholds, total_runs
from codeproof_ai.eval.pairing import PairVerdict, score_pairs
from codeproof_ai.eval.runner import ReviewerRun, regrade_view, run_reviewer
from codeproof_ai.reviewers.imported import ImportedReviewer

if TYPE_CHECKING:
    from codeproof_ai.eval.grading.base import Grader
    from codeproof_ai.eval.runner import SampleOutcome
    from codeproof_ai.eval.sample import LabeledSample

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"
D005 = "D005-half-open-contract"  # twin 결함 L9 · decoy 근거가 덮는 구간 L7-15
D001 = "D001-upstream-validated-dict-access"
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
    root.mkdir(parents=True)
    for sid, per_run in runs.items():
        for i, fs in enumerate(per_run):
            (root / f"{sid}.{i}.json").write_text(json.dumps({"findings": fs}), encoding="utf-8")
    n = len(next(iter(runs.values())))
    reviewer = ImportedReviewer(
        root, name="agent", identity="t", kind=ReviewerKind.AGENT, fmt="native"
    )
    graders: list[Grader] = [ProvableSafetyGrader(), InjectedDefectGrader(), PairedFixGrader()]
    return run_reviewer(reviewer, samples, graders, sample_n=n, harness_sha="test")


FLAKY: dict[str, list[list[dict[str, object]]]] = {
    D005: [[], [_llm(8, 9)]],                 # 두 번째 실행에서만 튄다
    f"{D005}#twin": [[_llm(9, 9)], [_llm(9, 9)]],
}


@pytest.fixture
def flaky(tmp_path: Path) -> ReviewerRun:
    return _run(tmp_path, FLAKY)


def _samples() -> list[LabeledSample]:
    return [s for s in load_decoy_samples(DECOYS) if s.sample_id in FLAKY]


def _grader(name: str) -> Grader:
    """새 채점자 - 관점 함수는 채점자를 복사해 다시 묶으므로 새것이어도 된다."""
    graders: dict[str, Grader] = {
        "provable_safety": ProvableSafetyGrader(),
        "injected_defect": InjectedDefectGrader(),
        "paired_fix": PairedFixGrader(),
    }
    return graders[name]


class TestViewsAreDifferentNumbers:
    def test_union_counts_a_one_off_finding(self, flaky: ReviewerRun) -> None:
        (pair,) = score_pairs(flaky.outcomes, G)
        assert pair.verdict is PairVerdict.OVER_FLAG

    def test_each_run_is_what_a_developer_sees(self, flaky: ReviewerRun) -> None:
        # 계약의 두 번째 줄 - 같은 데이터가 실행 0 에서는 구별 성공이다.
        g = [_grader(G)]
        (first,) = score_pairs(regrade_view(flaky.outcomes, _samples(), g, run=0), G)
        (second,) = score_pairs(regrade_view(flaky.outcomes, _samples(), g, run=1), G)
        assert (first.verdict, second.verdict) == (PairVerdict.CORRECT, PairVerdict.OVER_FLAG)

    def test_single_run_expectation_averages_the_runs(self, flaky: ReviewerRun) -> None:
        e = expectation(flaky.outcomes, _samples(), _grader(G))
        assert e.per_run == (1, 0)
        assert e.point == pytest.approx(0.5)

    def test_threshold_drops_the_one_off(self, flaky: ReviewerRun) -> None:
        assert at_least(flaky.outcomes, _samples(), _grader(G), 2).successes == 1
        assert at_least(flaky.outcomes, _samples(), _grader(G), 1).successes == 0

    def test_views_are_exclusive(self, flaky: ReviewerRun) -> None:
        with pytest.raises(ValueError, match="하나만"):
            regrade_view(flaky.outcomes, _samples(), [_grader(G)], run=0, at_least=2)

    def test_regrading_leaves_the_given_grader_unbound(self, flaky: ReviewerRun) -> None:
        """🔴 복사본을 묶는다 - 넘겨받은 채점자를 다시 묶으면 뒤의 채점이 관점의 짝을 본다."""
        g = PairedFixGrader()
        regrade_view(flaky.outcomes, _samples(), [g], run=0)
        with pytest.raises(UnboundGraderError):
            g.judge(_samples()[0], ())


class TestViewsMatchRunningAlone:
    """🔴 관점 값은 「그 실행만 돌렸다면」 나왔을 값이어야 한다 - 채점자와 무관하게.

    기준값은 실행기 경로를 한 번 더 타서 만든다 (그 실행의 지적만으로 sample_n=1).
    `paired_fix` 는 짝의 지적을 받아 판정하므로, 판정을 관점으로 **걸러내기만**
    하면 합집합 짝으로 내린 판정이 그대로 남는다.
    [실측 · claude n=8 · 60쌍] 그렇게 낸 단일 실행 기대값이 60.4% 로 발표됐다 -
    회차별 단독 채점의 평균은 62.7% 였고, 다른 채점자 셋은 일치했다.
    """

    GRADERS = ("provable_safety", "injected_defect", "paired_fix")

    @pytest.mark.parametrize("grader", GRADERS)
    def test_each_run(self, tmp_path: Path, flaky: ReviewerRun, grader: str) -> None:
        alone = []
        for r in range(2):
            run_r = _run(tmp_path / f"alone{r}", {sid: [rs[r]] for sid, rs in FLAKY.items()})
            (pair,) = score_pairs(run_r.outcomes, grader)
            alone.append(int(pair.verdict is PairVerdict.CORRECT))
        assert expectation(flaky.outcomes, _samples(), _grader(grader)).per_run == tuple(alone)

    @pytest.mark.parametrize("grader", GRADERS)
    def test_threshold(self, tmp_path: Path, flaky: ReviewerRun, grader: str) -> None:
        both = {sid: [[f for f in rs[0] if f in rs[1]]] for sid, rs in FLAKY.items()}
        (pair,) = score_pairs(_run(tmp_path / "both", both).outcomes, grader)
        expected = int(pair.verdict is PairVerdict.CORRECT)
        assert at_least(flaky.outcomes, _samples(), _grader(grader), 2).successes == expected


def _pair_samples(*sids: str) -> list[LabeledSample]:
    wanted = {x for s in sids for x in (s, f"{s}#twin")}
    return [s for s in load_decoy_samples(DECOYS) if s.sample_id in wanted]


class TestDifference:
    """🔴 리뷰어 비교는 같은 짝 위의 차이로 낸다 (DESIGN §7.10b).

    두 리뷰어의 구간을 눈으로 겹쳐 보지 않는다.
    """

    def test_point_is_the_difference_of_expectations(
        self, tmp_path: Path, flaky: ReviewerRun
    ) -> None:
        """실행 횟수가 달라도 된다 - 단일 실행 기대값은 N 과 무관한 양이다."""
        once = _run(tmp_path / "once", {sid: [rs[0]] for sid, rs in FLAKY.items()})
        d = difference(flaky.outcomes, once.outcomes, _samples(), _grader(G))
        a = expectation(flaky.outcomes, _samples(), _grader(G)).point
        b = expectation(once.outcomes, _samples(), _grader(G)).point
        assert a is not None and b is not None
        assert d.point == pytest.approx(a - b)

    def test_a_reviewer_against_itself_has_no_width(self, tmp_path: Path) -> None:
        """🔴 두 리뷰어를 같은 짝으로 함께 뽑는다.

        따로 뽑으면 자기 자신과의 차이에도 폭이 생긴다.
        """
        run = _run(tmp_path, {
            D005: [[]], f"{D005}#twin": [[_llm(9, 9)]],  # 구별 (P-C)
            D001: [[]], f"{D001}#twin": [[]],            # 둘 다 미지적 (P-B)
        })
        samples = _pair_samples(D005, D001)
        d = difference(run.outcomes, run.outcomes, samples, _grader(G))
        assert (d.point, d.interval, d.distinguishable) == (0.0, (0.0, 0.0), False)
        # 대조 - 같은 데이터의 기대값 구간은 폭이 있다. 짝마다 결과가 달라서다.
        e = expectation(run.outcomes, samples, _grader(G))
        assert e.interval is not None
        assert e.interval[0] < e.interval[1]

    def test_a_clear_gap_is_distinguishable(self, tmp_path: Path) -> None:
        good = _run(tmp_path / "good", {D005: [[]], f"{D005}#twin": [[_llm(9, 9)]]})
        over = _run(tmp_path / "over", {D005: [[_llm(8, 9)]], f"{D005}#twin": [[_llm(9, 9)]]})
        d = difference(good.outcomes, over.outcomes, _samples(), _grader(G))
        assert d.point == pytest.approx(1.0)
        assert d.distinguishable is True

    def test_different_pairs_are_refused(self, tmp_path: Path) -> None:
        a = _run(tmp_path / "a", {D005: [[]], f"{D005}#twin": [[_llm(9, 9)]]})
        b = _run(tmp_path / "b", {D001: [[]], f"{D001}#twin": [[]]})
        with pytest.raises(ValueError, match="짝이 다르다"):
            difference(a.outcomes, b.outcomes, _pair_samples(D005, D001), _grader(G))

    def test_deterministic(self, tmp_path: Path, flaky: ReviewerRun) -> None:
        once = _run(tmp_path / "once", {sid: [rs[0]] for sid, rs in FLAKY.items()})
        first = difference(flaky.outcomes, once.outcomes, _samples(), _grader(G))
        assert first == difference(flaky.outcomes, once.outcomes, _samples(), _grader(G))


class TestExpectationInterval:
    def test_deterministic(self, flaky: ReviewerRun) -> None:
        # 🔴 생성물에 실리는 값이다 - 돌릴 때마다 달라지면 「최신인가」를 물을 수 없다.
        e1 = expectation(flaky.outcomes, _samples(), _grader(G))
        assert e1 == expectation(flaky.outcomes, _samples(), _grader(G))

    def test_interval_contains_the_point(self, flaky: ReviewerRun) -> None:
        e = expectation(flaky.outcomes, _samples(), _grader(G))
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
