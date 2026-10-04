"""모델·에이전트 모양의 지적이 채점 경로를 어떻게 지나는가.

LLM 지적은 정적분석기와 모양이 다르다 - **줄 범위**를 주고, 룰 코드 대신
category 를 주고, 둘러싼 심볼이 없다. 합성 샘플로는 그 모양이 실제로 무엇을
깨는지 놓치므로 **실제 코퍼스 짝**으로 본다.

[실측 · 34쌍] 두 가지가 조용히 틀려 있었다.
  1. 채점자가 시작 줄만 봤다 - claude 는 `def` 줄부터 범위를 잡으므로
     slack=0 에서 탐지 19쌍이 빠지고 claude/codex 순위가 뒤집혔다.
  2. 짝 채점이 `(category, None)` 으로 「같은 지적」을 판정했다 - 파일 안
     같은 category 면 다른 함수의 다른 주장도 같은 지적이 됐다 (D005).
"""

from __future__ import annotations

import json
from pathlib import Path

from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.eval.grading.base import Grader, Outcome
from codeproof_ai.eval.grading.injected import InjectedDefectGrader
from codeproof_ai.eval.grading.paired import PairedFixGrader
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import PRESENTED_FILENAME, load_decoy_samples
from codeproof_ai.eval.runner import ReviewerRun, run_reviewer
from codeproof_ai.reviewers.imported import ImportedReviewer

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"
D003 = "D003-caller-held-lock"  # twin 결함 L16 (bump 본문), 미끼 L10-12
D005 = "D005-half-open-contract"  # twin 결함 L11 (page_bounds), 미끼 L16-17 (slice_page)


def _llm(start: int, end: int, category: str = "correctness") -> dict[str, object]:
    return {
        "file": PRESENTED_FILENAME, "line_start": start, "line_end": end,
        "category": category, "severity": "error", "quoted_code": f"L{start}-{end}",
        "message": "m", "failure_mode": "f",
    }


def _run(
    tmp_path: Path,
    pair: str,
    decoy: list[dict[str, object]],
    twin: list[dict[str, object]],
) -> ReviewerRun:
    samples = [
        s for s in load_decoy_samples(DECOYS) if s.sample_id in (pair, f"{pair}#twin")
    ]
    root = tmp_path / "out"
    root.mkdir()
    for sid, fs in ((pair, decoy), (f"{pair}#twin", twin)):
        (root / f"{sid}.0.json").write_text(json.dumps({"findings": fs}), encoding="utf-8")
    reviewer = ImportedReviewer(
        root, name="agent", identity="t", kind=ReviewerKind.AGENT, fmt="native"
    )
    graders: list[Grader] = [ProvableSafetyGrader(), InjectedDefectGrader(), PairedFixGrader()]
    return run_reviewer(reviewer, samples, graders, sample_n=1, harness_sha="test")


def _outcomes(run: ReviewerRun, sid: str, grader: str) -> list[Outcome]:
    o = next(o for o in run.outcomes if o.sample_id == sid)
    return [j.outcome for j in o.judgments[grader]]


class TestReportedRangeIsTheLocation:
    """채점자는 지적의 **보고 범위**가 결함 구간에 닿는지 본다 (slack=0)."""

    def test_function_range_ending_on_the_defect_is_a_detection(
        self, tmp_path: Path
    ) -> None:
        # claude 의 실제 보고 모양: `def bump` 줄부터 결함 줄까지.
        run = _run(tmp_path, D003, [], [_llm(15, 16, "concurrency")])
        assert _outcomes(run, f"{D003}#twin", "injected_defect") == [Outcome.TRUE_POSITIVE]

    def test_range_away_from_the_defect_is_not(self, tmp_path: Path) -> None:
        run = _run(tmp_path, D003, [], [_llm(5, 6, "concurrency")])
        assert _outcomes(run, f"{D003}#twin", "injected_defect") != [Outcome.TRUE_POSITIVE]

    def test_the_decoy_side_uses_the_same_rule(self, tmp_path: Path) -> None:
        """⚠ 대칭이다 - 넓게 잡은 범위는 안전 근거가 덮는 구간에도 닿는다.

        D005 의 근거는 가드 L7-12 와 미끼 L16-17 을 덮는다. L3-7 은 **시작 줄이 밖**이라
        예전 규칙이면 판정 불가였다 - 범위로 보면 닿으므로 거짓 경보다.
        """
        run = _run(tmp_path, D005, [_llm(3, 7), _llm(3, 3)], [])
        assert _outcomes(run, D005, "provable_safety") == [
            Outcome.FALSE_POSITIVE,
            Outcome.UNDECIDABLE,
        ]


class TestSameFindingAcrossThePair:
    """짝 채점의 「짝에도 같은 지적」은 (category, **둘러싼 함수**) 로 본다."""

    def test_llm_findings_get_the_enclosing_function(self, tmp_path: Path) -> None:
        run = _run(tmp_path, D005, [], [_llm(11, 11)])
        twin = next(o for o in run.outcomes if o.sample_id == f"{D005}#twin")
        assert [ob.finding.location.symbol for ob in twin.observations.observed] == [
            "page_bounds"
        ]

    def test_same_category_in_another_function_is_a_different_finding(
        self, tmp_path: Path
    ) -> None:
        # [실측] claude D005: decoy 는 slice_page 쪽, twin 은 page_bounds 쪽.
        # 심볼 없이 비교했을 때 이 탐지가 「짝에도 있다」로 지워졌다.
        run = _run(tmp_path, D005, [_llm(16, 17)], [_llm(11, 11)])
        assert _outcomes(run, f"{D005}#twin", "paired_fix") == [Outcome.TRUE_POSITIVE]

    def test_same_category_in_the_same_function_is_not_discriminating(
        self, tmp_path: Path
    ) -> None:
        # 계약의 두 번째 줄 - 같은 함수에서 양쪽 다 지적했으면 구별한 것이 아니다.
        run = _run(tmp_path, D005, [_llm(10, 11)], [_llm(11, 11)])
        assert _outcomes(run, f"{D005}#twin", "paired_fix") == [Outcome.UNDECIDABLE]
