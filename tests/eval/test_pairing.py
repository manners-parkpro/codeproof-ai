"""짝 채점 - 과잉지적은 짝을 지어야만 보인다."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeproof_ai.analysis.python.ruff import RuffAnalyzer
from codeproof_ai.domain.observation import ObservationSet
from codeproof_ai.eval.grading.base import Judgment, Outcome
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.eval.pairing import (
    PairVerdict,
    discrimination_rate,
    pair_summary,
    score_pairs,
)
from codeproof_ai.eval.runner import SampleOutcome, run_reviewer
from codeproof_ai.reviewers.wrap import AnalyzerReviewer

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"
G = "provable_safety"


def _outcome(sid: str, *, safe: bool, outcomes: list[Outcome]) -> SampleOutcome:
    return SampleOutcome(
        sample_id=sid,
        is_proven_safe=safe,
        observations=ObservationSet(
            target_id=sid, reviewer="ruff", total_runs=1, grouper="fingerprint",
            observed=(),
        ),
        judgments={G: tuple(Judgment(f"k{i}", o, G) for i, o in enumerate(outcomes))},
    )


def _pair(neg: list[Outcome], pos: list[Outcome]) -> PairVerdict:
    got = score_pairs(
        [
            _outcome("d", safe=True, outcomes=neg),
            _outcome("d#twin", safe=False, outcomes=pos),
        ],
        G,
    )
    assert len(got) == 1
    return got[0].verdict


class TestAGraderThatDidNotGrade:
    def test_its_name_is_refused(self) -> None:
        """🔴 틀린 이름은 KeyError 다 - `.get(…, ())` 은 모든 짝을 「놓침」(P-B)으로 바꿨다."""
        outcomes = [
            _outcome("d", safe=True, outcomes=[]),
            _outcome("d#twin", safe=False, outcomes=[Outcome.TRUE_POSITIVE]),
        ]
        assert score_pairs(outcomes, G)[0].verdict is PairVerdict.CORRECT
        with pytest.raises(KeyError):
            score_pairs(outcomes, "provable-safety")


class TestFourVerdicts:
    def test_correct_discrimination(self) -> None:
        """양성만 지적 - 유일하게 옳은 결과."""
        assert _pair([], [Outcome.TRUE_POSITIVE]) is PairVerdict.CORRECT

    def test_over_flagging(self) -> None:
        """🔴 둘 다 지적 - 구별하지 못했다. per-finding 으로는 안 보인다."""
        assert (
            _pair([Outcome.FALSE_POSITIVE], [Outcome.TRUE_POSITIVE])
            is PairVerdict.OVER_FLAG
        )

    def test_under_flagging(self) -> None:
        assert _pair([], []) is PairVerdict.UNDER_FLAG

    def test_reversed(self) -> None:
        assert _pair([Outcome.FALSE_POSITIVE], []) is PairVerdict.REVERSED


class TestUndecidableIsNotSilence:
    def test_undecidable_on_positive_is_not_detection(self) -> None:
        """판정 불가는 '지적했다' 가 아니다 - 판정 범위 밖일 뿐이다."""
        assert _pair([], [Outcome.UNDECIDABLE]) is PairVerdict.UNDER_FLAG

    def test_undecidable_on_negative_is_not_a_false_positive(self) -> None:
        assert (
            _pair([Outcome.UNDECIDABLE], [Outcome.TRUE_POSITIVE])
            is PairVerdict.CORRECT
        )


class TestPairingRequiresBothSides:
    def test_unpaired_sample_is_skipped(self) -> None:
        assert score_pairs([_outcome("d", safe=True, outcomes=[])], G) == ()

    def test_positive_without_negative_is_skipped(self) -> None:
        assert score_pairs([_outcome("d#twin", safe=False, outcomes=[])], G) == ()


class TestPerFindingHidesWhatPairingShows:
    """🔴 이 테스트가 짝 채점의 존재 이유다."""

    def test_same_rule_on_both_sides_looks_fine_per_finding(self) -> None:
        neg = _outcome("d", safe=True, outcomes=[Outcome.FALSE_POSITIVE])
        pos = _outcome("d#twin", safe=False, outcomes=[Outcome.TRUE_POSITIVE])

        # per-finding: TP 1 · FP 1 -> Precision 50%, 양성 쪽만 보면 100%
        tp = sum(
            1 for j in pos.judgments[G] if j.outcome is Outcome.TRUE_POSITIVE
        )
        assert tp == 1, "양성 쪽만 보면 완벽해 보인다"

        # 짝: 구별 실패
        assert score_pairs([neg, pos], G)[0].verdict is PairVerdict.OVER_FLAG


class TestAgainstShippedCorpus:
    def test_ruff_discriminates_poorly(self) -> None:
        """실측 - Ruff 가 구별하는 쌍은 위험 패턴이 twin 에만 남는 경우뿐이다.

        [실측 · 74쌍] 기본 룰로 구별한 쌍은 D067 하나다 - 가드를 지우자 twin 에
        `except Exception: continue` 만 남아 S112 가 twin 에서만 운다. 나머지는 둘 다
        침묵하거나(P-B) 둘 다 지적하거나(P-V) 안전한 쪽만 지적한다(P-R).
        [실측 · 130쌍] D123 이 같은 꼴로 더해졌다 - 가드(_classify)를 지운 twin 에
        `except Exception: pass` 만 남아 S110 이 twin 에서만 운다.

        🔴 개수가 아니라 **어느 쌍인지**를 본다. 구별한 쌍이 바뀌면 코퍼스나 분석기가
           바뀐 것이다 - 그 쌍의 지적을 열어 보고 갱신한다.
        """
        samples = load_decoy_samples(DECOYS)
        run = run_reviewer(
AnalyzerReviewer(RuffAnalyzer()), samples, [ProvableSafetyGrader()], harness_sha="test"
        )
        pairs = score_pairs(run.outcomes, G)
        _, total = discrimination_rate(pairs)

        assert total == len(samples) // 2, "모든 decoy 가 짝을 이뤄야 한다"
        discriminated = {p.pair_id for p in pairs if p.verdict is PairVerdict.CORRECT}
        assert discriminated == {
            "D067-only-best-effort-hooks-are-swallowed",
            "D123-only-transient-errors-retried",
        }, (
            f"Ruff 가 구별한 쌍이 바뀌었다: {sorted(discriminated)} - 실측이 바뀌었다"
        )

        counts = pair_summary(pairs)
        assert counts[PairVerdict.OVER_FLAG] >= 1, "D002 의 P-V 가 사라졌다"

    def test_every_decoy_has_a_twin(self) -> None:
        samples = load_decoy_samples(DECOYS)
        ids = {s.sample_id for s in samples}
        for s in samples:
            assert s.paired_with in ids, f"{s.sample_id} 의 짝이 없다"
