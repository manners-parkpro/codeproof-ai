"""교차 저자 분석 - 선언한 읽는 법 · twin 쪽 판정 묶음 · 거절 조건 (DESIGN §7.10d 준비 ⑧).

🔴 읽는 법의 갈래마다 하나씩 본다 - 갈래 하나가 다른 갈래로 접히면 결론 문장이 바뀐다.
   배관(CLI · 생성물 · --check)은 `tests/cli/test_commands.py::TestXauthorReport` 가 본다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.eval import crossauthor
from codeproof_ai.eval.crossauthor import (
    PRIMARY,
    READINGS,
    TWIN,
    Reading,
    Rung,
    by_kind,
    findings_per_sample,
    gap,
    ladder,
    problems,
    read,
    without,
)
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import PRESENTED_FILENAME, load_decoy_samples
from codeproof_ai.eval.multirun import Difference
from codeproof_ai.eval.pairing import PairVerdict as V
from codeproof_ai.eval.report import SETUP_KEYS, AgentSection
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.eval.sensitivity import DEFAULT_SWEEP
from codeproof_ai.reviewers.imported import ImportedReviewer

if TYPE_CHECKING:
    from codeproof_ai.eval.sample import LabeledSample

ABOVE = (0.05, 0.30)
AROUND = (-0.05, 0.20)
BELOW = (-0.30, -0.05)
FLIPPED = (-0.20, 0.05)
"""0 을 품되 점추정이 음수 - AROUND 와 판정은 같고 부호만 다르다."""


def _ladder(*bounds: tuple[float, float]) -> tuple[Rung, ...]:
    return tuple(
        Rung(s, 0.5, 0.5, Difference(pairs=10, point=(lo + hi) / 2, interval=(lo, hi)))
        for s, (lo, hi) in zip(DEFAULT_SWEEP, bounds, strict=True)
    )


def _flat(bounds: tuple[float, float]) -> tuple[Rung, ...]:
    return _ladder(*[bounds] * len(DEFAULT_SWEEP))


class TestTheReadingIsTheDeclaredOne:
    """§7.10d 「읽는 법」 ①②③ 과 §7.10b 의 「흔들린다」."""

    def test_both_above_on_every_rung_is_reading_one(self) -> None:
        assert read(_flat(ABOVE), _flat(ABOVE)) is Reading.BOTH

    def test_the_twin_side_must_hold_on_every_rung(self) -> None:
        """🔴 twin 쪽 차이는 사다리 **모든 칸**에서 0 보다 커야 한다 - 첫 칸만 보면 ① 이 된다."""
        twin = _ladder(ABOVE, ABOVE, ABOVE, AROUND)
        assert read(_flat(ABOVE), twin) is Reading.PRIMARY_ONLY

    def test_a_lead_without_the_twin_side_is_unconfirmed(self) -> None:
        assert read(_flat(ABOVE), _flat(AROUND)) is Reading.PRIMARY_ONLY

    def test_an_interval_around_zero_is_indistinct(self) -> None:
        assert read(_flat(AROUND), _flat(ABOVE)) is Reading.INDISTINCT

    def test_below_zero_is_codex_ahead(self) -> None:
        assert read(_flat(BELOW), _flat(BELOW)) is Reading.CODEX_AHEAD

    def test_a_verdict_change_on_the_ladder_is_shaky(self) -> None:
        """🔴 §7.10b 와 같은 규칙 - 주 지표의 판정이 바뀌면 twin 쪽이 좋아도 결론이 없다."""
        assert read(_ladder(ABOVE, ABOVE, AROUND, AROUND), _flat(ABOVE)) is Reading.SHAKY

    def test_a_sign_change_inside_zero_is_shaky(self) -> None:
        assert read(_ladder(AROUND, AROUND, FLIPPED, FLIPPED), _flat(AROUND)) is Reading.SHAKY

    def test_every_branch_has_its_declared_sentence(self) -> None:
        assert set(READINGS) == set(Reading)


class TestTheTwinSideCountsEveryCaughtTwin:
    def test_flagging_both_sides_still_caught_the_twin(self) -> None:
        """🔴 twin 쪽 = twin 을 짚은 짝 (P-C · P-V). P-V 를 빼면 주 지표와 같은 묶음이 된다."""
        a = [{"p1": V.OVER_FLAG, "p2": V.CORRECT}]
        b = [{"p1": V.UNDER_FLAG, "p2": V.REVERSED}]
        scored = dict.fromkeys(DEFAULT_SWEEP, (a, b))
        twin, primary = ladder(scored, TWIN)[0], ladder(scored, PRIMARY)[0]
        assert (twin.a, twin.b) == (1.0, 0.0)
        assert (primary.a, primary.b) == (0.5, 0.0)


class TestDescriptives:
    def test_each_kind_is_scored_on_its_own_pairs(self) -> None:
        a = [{"p1": V.CORRECT, "p2": V.UNDER_FLAG, "p3": V.CORRECT}]
        b = [{"p1": V.UNDER_FLAG, "p2": V.UNDER_FLAG, "p3": V.UNDER_FLAG}]
        rows = by_kind((a, b), {"p1": "k1", "p2": "k1", "p3": "k2"})
        assert [(k, n, r.a, r.b) for k, n, r in rows] == [("k1", 2, 0.5, 0.0), ("k2", 1, 1.0, 0.0)]

    def test_the_sensitivity_drops_only_the_listed_pairs(self) -> None:
        a = [{"p1": V.CORRECT, "p2": V.CORRECT, "p3": V.UNDER_FLAG}]
        b = [{"p1": V.UNDER_FLAG, "p2": V.UNDER_FLAG, "p3": V.UNDER_FLAG}]
        r = without((a, b), frozenset({"p1"}))
        assert (r.difference.pairs, r.a, r.b) == (2, 0.5, 0.0)

    def test_the_size_gap_resamples_each_corpus_on_its_own(self) -> None:
        same = gap([0.2] * 5, [0.1] * 7)
        assert same.point == pytest.approx(0.1)
        assert same.interval == pytest.approx((0.1, 0.1))
        mixed = gap([0.0, 1.0] * 5, [0.0] * 4)
        assert mixed.interval[0] < mixed.point < mixed.interval[1]


DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"
ONE_PER_KIND = (
    "D001-upstream-validated-dict-access",  # upstream_validation
    "D006-emptiness-narrowed",              # type_narrowed
    "D002-shell-true-constant-command",     # constant_only_sink
)
SECOND_OF_A_KIND = "D013-eval-on-literal"   # constant_only_sink


def _samples(*pairs: str) -> list[LabeledSample]:
    return [s for s in load_decoy_samples(DECOYS) if s.sample_id.split("#")[0] in pairs]


def _finding(line: int, category: str) -> dict[str, object]:
    return {
        "file": PRESENTED_FILENAME, "line_start": line, "line_end": line,
        "category": category, "severity": "error", "quoted_code": f"L{line}",
        "message": "m", "failure_mode": "f",
    }


def _section(
    tmp_path: Path,
    samples: list[LabeledSample],
    *,
    agent: str = "claude",
    runs: int = 3,
    docstrings: str = "neutral",
    cli: str = "1.0",
    findings: dict[bool, list[list[dict[str, object]]]] | None = None,
) -> AgentSection:
    """실행기 출력 모양으로 쓰고 `run_reviewer` 로 재생한 실행 - `findings` 는 decoy 여부별."""
    root = tmp_path / f"{agent}-{runs}-{docstrings}-{cli}"
    root.mkdir(parents=True)
    for s in samples:
        per_run = (findings or {}).get(s.is_proven_safe, [[] for _ in range(runs)])
        for i, fs in enumerate(per_run):
            (root / f"{s.sample_id}.{i}.json").write_text(
                json.dumps({"findings": fs}), encoding="utf-8"
            )
    reviewer = ImportedReviewer(
        root, name=f"{agent}-x", identity="t", kind=ReviewerKind.AGENT, fmt="native"
    )
    run = run_reviewer(
        reviewer, samples, [ProvableSafetyGrader()], sample_n=runs, harness_sha="test"
    )
    setup = tuple((k, cli if k == "cli_version" else "same") for k in SETUP_KEYS)
    return AgentSection(
        run=run, graders=(), rejected=0, agent=agent, docstrings=docstrings, setup=setup
    )


class TestTheDeclaredNumbersArePinned:
    def test_runs_knob_pairs_per_kind_and_floor(self) -> None:
        """선언 「측정」 · 「2단계」 - 3회 · neutral · 분류마다 8쌍 · 8분류 미만은 「미완」.

        🔴 하한은 10 에서 8 로 낮췄다 (수집 중 보정 2026-10-09). 실행기 하한
           (`xauthor_run.MIN_KINDS`)과 갈리면 실행기는 2단계를 정상 종료하는데 옮기기 · 보고서가
           「미완」이 된다. 다른 시험은 이 값들을 바꿔 끼워 써서 고정하지 못한다.
        """
        got = (crossauthor.RUNS, crossauthor.DOCSTRINGS, crossauthor.PAIRS_PER_KIND,
               crossauthor.MIN_KINDS)
        assert got == (3, "neutral", 8, 8)


class TestTheInputMustBeTheDeclaredOne:
    """🔴 선언과 다른 입력은 「미완」이다 - 값을 내지 않는다 (§7.10d 「측정」)."""

    @pytest.fixture(autouse=True)
    def _one_pair_per_kind(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(crossauthor, "PAIRS_PER_KIND", 1)
        monkeypatch.setattr(crossauthor, "MIN_KINDS", len(ONE_PER_KIND))

    def _pairs(
        self, tmp_path: Path, samples: list[LabeledSample], **claude: object
    ) -> tuple[tuple[AgentSection, AgentSection], tuple[AgentSection, AgentSection]]:
        measured = (
            _section(tmp_path / "x", samples, **claude),  # type: ignore[arg-type]
            _section(tmp_path / "x", samples, agent="codex"),
        )
        reference = (
            _section(tmp_path / "r", samples),
            _section(tmp_path / "r", samples, agent="codex"),
        )
        return measured, reference

    def test_the_declared_input_passes(self, tmp_path: Path) -> None:
        """대조 - 아래 거절이 무엇에나 우는 검사가 아님을 보인다."""
        samples = _samples(*ONE_PER_KIND)
        measured, reference = self._pairs(tmp_path, samples)
        assert problems(measured, reference, samples, {}) == []

    def test_another_cli_version_is_refused(self, tmp_path: Path) -> None:
        """🔴 격리 설치한 판 대신 다른 판으로 재면 목표 150쌍과 같은 설정이 아니다."""
        samples = _samples(*ONE_PER_KIND)
        measured, reference = self._pairs(tmp_path, samples, cli="2.0")
        (found,) = problems(measured, reference, samples, {})
        assert "`cli_version` 1.0 → 2.0" in found

    def test_the_runs_and_the_knob_are_the_declared_ones(self, tmp_path: Path) -> None:
        samples = _samples(*ONE_PER_KIND)
        measured, reference = self._pairs(tmp_path, samples, runs=2, docstrings="keep")
        found = problems(measured, reference, samples, {})
        assert any("2회다" in p for p in found)
        assert any("`keep`" in p for p in found)

    def test_every_kind_must_be_full(self, tmp_path: Path) -> None:
        """🔴 채우지 못한 분류의 쌍이 섞이면 분류 구성비가 선언과 달라진다 (F5a)."""
        samples = _samples(*ONE_PER_KIND, SECOND_OF_A_KIND)
        measured, reference = self._pairs(tmp_path, samples)
        (found,) = problems(measured, reference, samples, {})
        assert "`constant_only_sink` 2쌍" in found

    def test_too_few_kinds_is_unfinished(self, tmp_path: Path) -> None:
        samples = _samples(*ONE_PER_KIND[:2])
        measured, reference = self._pairs(tmp_path, samples)
        (found,) = problems(measured, reference, samples, {})
        assert "분류가 2개다" in found

    def test_an_unknown_pair_in_an_issue_list_is_refused(self, tmp_path: Path) -> None:
        """🔴 오타가 조용히 「뺀 쌍 0」이 되면 민감도가 주 지표와 같아 보인다."""
        samples = _samples(*ONE_PER_KIND)
        measured, reference = self._pairs(tmp_path, samples)
        issues = {"a": frozenset({ONE_PER_KIND[0], "D999-typo"})}
        (found,) = problems(measured, reference, samples, issues)
        assert "D999-typo" in found


def test_findings_are_counted_per_run_on_each_side(tmp_path: Path) -> None:
    """샘플당 지적 수는 회차 평균이다 - 합집합 크기가 아니다."""
    samples = _samples(ONE_PER_KIND[0])
    found = {
        True: [[_finding(1, "correctness")], [], []],
        False: [[_finding(1, "correctness"), _finding(2, "security")]] * 3,
    }
    run = _section(tmp_path, samples, findings=found).run
    decoy, twin = (findings_per_sample(run, decoy=d) for d in (True, False))
    assert decoy.n == 1
    assert decoy.point == pytest.approx(1 / 3)
    assert (twin.n, twin.point) == (1, 2.0)
