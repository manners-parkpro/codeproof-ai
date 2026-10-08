"""대시보드의 기록된 리뷰 - 점수판과 같은 판정 · 회차마다 그 회차의 원문 · 고르지 않은 전부.

🔴 화면이 센 값과 모순되면 안 된다. 원문마다의 판정으로 다시 만든 짝 판정이 점수판의 회차별
   판정과 다르면 만들지 않는다 - 그 대조가 실제로 우는지 본다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from codeproof_ai.analysis.python.ruff import SYNTAX_ERROR
from codeproof_ai.corpus.decoy import TrapKind
from codeproof_ai.domain.finding import Category, Finding, Severity
from codeproof_ai.domain.location import Location, Position, Span
from codeproof_ai.domain.reviewer import ReviewerKind
from codeproof_ai.eval import explorer
from codeproof_ai.eval.export import neutral_docstring
from codeproof_ai.eval.grading.base import Outcome
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import PRESENTED_FILENAME, load_decoy_samples
from codeproof_ai.eval.pairing import PairVerdict
from codeproof_ai.eval.report import SETUP_KEYS, AgentSection
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.reviewers.imported import ImportedReviewer

if TYPE_CHECKING:
    from codeproof_ai.eval.sample import LabeledSample

ROOT = Path(__file__).resolve().parents[2]
DECOYS = ROOT / "corpus" / "decoys"
D117 = "D117-page-size-capped-before-slicing"  # twin 결함 L9 · decoy 가드 L9 · 덮는 범위 L9-10


def _finding(line: int, end: int, category: Category = Category.CORRECTNESS) -> Finding:
    return Finding(
        source="t", rule_id="X", message="m",
        location=Location(path=PRESENTED_FILENAME, span=Span(
            start=Position(line=line, column=0), end=Position(line=end, column=0),
        )),
        category=category, severity=Severity.WARNING, quoted_code="x",
    )


def _llm(start: int, end: int, category: str = "correctness") -> dict[str, object]:
    return {
        "file": PRESENTED_FILENAME, "line_start": start, "line_end": end,
        "category": category, "severity": "error", "quoted_code": f"L{start}",
        "message": f"L{start}-{end} 를 짚었다", "failure_mode": "f",
    }


def _section(
    tmp_path: Path, agent: str, runs: dict[str, list[list[dict[str, object]]]]
) -> AgentSection:
    samples = [s for s in load_decoy_samples(DECOYS) if s.sample_id in runs]
    root = tmp_path / agent
    root.mkdir()
    for sid, per_run in runs.items():
        for i, fs in enumerate(per_run):
            (root / f"{sid}.{i}.json").write_text(json.dumps({"findings": fs}), encoding="utf-8")
    reviewer = ImportedReviewer(
        root, name=f"{agent}-x", identity="t", kind=ReviewerKind.AGENT, fmt="native"
    )
    n = len(next(iter(runs.values())))
    run = run_reviewer(reviewer, samples, [ProvableSafetyGrader()], sample_n=n, harness_sha="t")
    setup = tuple((k, "same") for k in SETUP_KEYS)
    return AgentSection(
        run=run, graders=(), rejected=0, agent=agent, docstrings="neutral", setup=setup
    )


def _samples() -> list[LabeledSample]:
    return [s for s in load_decoy_samples(DECOYS) if s.sample_id.split("#")[0] == D117]


Runs = dict[str, list[list[dict[str, object]]]]
CLAUDE: Runs = {  # 1회차는 결함을 짚고, 2회차는 안전한 쪽 덮는 범위에도 하나 낸다 (헛경고 + 짚음)
    D117: [[], [_llm(10, 10)]],
    f"{D117}#twin": [[_llm(7, 9)], [_llm(9, 9), _llm(1, 1, "style")]],
}
CODEX: Runs = {D117: [[], []], f"{D117}#twin": [[], [_llm(3, 3)]]}


@pytest.fixture
def data(tmp_path: Path) -> dict[str, Any]:
    pair = (_section(tmp_path, "claude", CLAUDE), _section(tmp_path, "codex", CODEX))
    return explorer.load(explorer.reviews(pair, _samples(), featured=[D117, "D999-gone"]))


class TestEachRunShowsWhatThatRunSaid:
    def test_verdicts_follow_the_scoreboard(self, data: dict[str, Any]) -> None:
        (pair,) = data["pairs"]
        claude, codex = pair["reviews"]
        assert [r["verdict"] for r in claude] == ["P-C", "P-V"]
        assert [r["verdict"] for r in codex] == ["P-B", "P-B"]

    def test_marks_say_why_a_finding_was_not_scored(self, data: dict[str, Any]) -> None:
        """🔴 관례 주장(`style`)과 정답 라벨 밖(`out`)은 다른 이유다 - 화면이 둘을 가른다."""
        (pair,) = data["pairs"]
        second = pair["reviews"][0][1]
        assert [row[3] for row in second["safe"]] == ["fp"]
        assert sorted(row[3] for row in second["buggy"]) == ["style", "tp"]
        assert [row[3] for row in pair["reviews"][1][1]["buggy"]] == ["out"]

    def test_lines_and_code_are_what_the_reviewer_saw(self, data: dict[str, Any]) -> None:
        (pair,) = data["pairs"]
        safe, buggy = (s for s in _samples() if not s.defects), (s for s in _samples() if s.defects)
        assert pair["safe"]["code"] == neutral_docstring(next(safe).target.files[0].content)
        assert pair["buggy"]["code"] == neutral_docstring(next(buggy).target.files[0].content)
        assert (pair["safe"]["guard"], pair["safe"]["covered"], pair["buggy"]["defect"]) == (
            [9, 9], [9, 10], [9, 9],
        )

    def test_featured_pairs_are_only_measured_ones(self, data: dict[str, Any]) -> None:
        assert data["featured"] == [D117]

    def test_a_verdict_the_scoreboard_did_not_count_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """🔴 원문으로 다시 만든 짝 판정이 점수판과 다르면 만들지 않는다 - 센 값과 모순된다."""
        pair = (_section(tmp_path, "claude", CLAUDE), _section(tmp_path, "codex", CODEX))
        monkeypatch.setattr(explorer, "_verdict", lambda *_: PairVerdict.UNDER_FLAG)
        with pytest.raises(ValueError, match="점수판"):
            explorer.reviews(pair, _samples())


class TestMarks:
    @pytest.mark.parametrize(
        ("outcome", "category", "mark"),
        [
            (Outcome.TRUE_POSITIVE, Category.CORRECTNESS, "tp"),
            (Outcome.FALSE_POSITIVE, Category.SECURITY, "fp"),
            (Outcome.UNDECIDABLE, Category.STYLE, "style"),
            (Outcome.UNDECIDABLE, Category.CORRECTNESS, "out"),
        ],
    )
    def test_each_outcome(self, outcome: Outcome, category: Category, mark: str) -> None:
        assert explorer._mark(outcome, _finding(1, 1, category)) == mark

    def test_every_trap_kind_has_a_plain_label(self) -> None:
        assert set(explorer.KIND_LABELS) == set(TrapKind)


class TestRuffRules:
    def test_only_convention_rules_are_listed(self) -> None:
        loaded = explorer.load(explorer.ruff_rules(
            "9.9.9", {"D103": Category.STYLE, "S605": Category.SECURITY},
        ))
        assert (loaded["version"], loaded["convention"]) == ("9.9.9", ["D103"])

    def test_the_syntax_code_is_the_adapters(self) -> None:
        """구문 오류는 룰이 아니다 - 화면이 결함 주장으로 세지 않게 어댑터와 같은 코드를 싣는다."""
        loaded = explorer.load(explorer.ruff_rules("9.9.9", {"D103": Category.STYLE}))
        assert loaded["syntax"] == SYNTAX_ERROR

    def test_no_categories_is_refused(self) -> None:
        """🔴 빈 표는 브라우저의 모든 지적을 결함 주장으로 보이게 한다."""
        with pytest.raises(ValueError, match="분류"):
            explorer.ruff_rules("9.9.9", {})


class TestTheShippedData:
    """저장소의 생성물 - 잰 짝 전부 · 알려진 값만 (`report --check` 가 최신인지 본다)."""

    def _load(self, name: str) -> dict[str, Any]:
        return explorer.load((ROOT / "docs" / "data" / name).read_text(encoding="utf-8"))

    def test_every_measured_pair_is_shown(self) -> None:
        """🔴 고르지 않는다 - 묶음이 잰 짝 전부다."""
        packs = sorted((ROOT / "results" / "agent").glob("*/RUN.json"))
        measured = {
            sid
            for p in packs
            for sid in json.loads(p.read_text(encoding="utf-8"))["packed_samples"]
            if "#" not in sid
        }
        data = self._load(explorer.REVIEWS)
        ids = [p["id"] for p in data["pairs"]]
        assert ids == sorted(measured)
        assert set(data["featured"]) <= set(ids)

    def test_unscored_claims_lie_outside_the_labeled_range(self) -> None:
        """화면은 채점하지 않은 결함 주장(`out`)에 정답 구간까지의 거리를 적는다 - 겹치면 그 거리가
        거짓이다. 원문의 줄(`_lines`)이 채점자의 겹침 규칙과 같은지도 여기서 드러난다."""
        data = self._load(explorer.REVIEWS)
        checked = 0
        for pair in data["pairs"]:
            refs = {"safe": pair["safe"]["covered"], "buggy": pair["buggy"]["defect"]}
            for run in (r for runs in pair["reviews"] for r in runs):
                for side, ref in refs.items():
                    for row in (row for row in run[side] if row[3] == "out"):
                        checked += 1
                        assert row[1] < ref[0] or row[0] > ref[1], (pair["id"], side, row[:2])
        assert checked, "범위 밖 지적이 없다 - 대조가 공허하다"

    def test_rows_use_known_values(self) -> None:
        data = self._load(explorer.REVIEWS)
        verdicts = {v.value for v in PairVerdict}
        for pair in data["pairs"]:
            for runs in pair["reviews"]:
                for run in runs:
                    assert run["verdict"] in verdicts
                    for row in run["safe"] + run["buggy"]:
                        assert row[0] <= row[1]
                        assert row[3] in {"tp", "fp", "style", "out"}
                    assert not any(row[3] == "tp" for row in run["safe"])
                    assert not any(row[3] == "fp" for row in run["buggy"])
