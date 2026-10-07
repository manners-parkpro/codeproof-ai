"""정답이 없는 코드의 리뷰 보고서 (`codeproof review`) - 지적과 근거만 내고 채점하지 않는다.

🔴 이 보고서가 「결함 확인」으로 읽히면 이 저장소가 비판하는 오류(증거의 부재를 부재의 증거로)를
   스스로 저지르는 것이다 - 문면과 채점 거부를 둘 다 테스트가 고정한다.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from codeproof_ai import review
from codeproof_ai.analysis.registry import create_analyzer
from codeproof_ai.cli import main
from codeproof_ai.domain.evidence import EvidenceKind, Verdict
from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.eval.sample import LabeledSample, Stratum
from codeproof_ai.review import ReviewError, render_review, review_file
from codeproof_ai.reviewers.wrap import AnalyzerReviewer

if TYPE_CHECKING:
    from pathlib import Path

SHELL = (
    "import os\nimport subprocess\n\n\n"
    "def run(cmd):\n    return subprocess.run(cmd, shell=True)\n"
)
BOTH = "def f() -> int:\n    return undefined_name\n"
"""Ruff(F821) 와 mypy(name-defined) 가 같은 줄을 짚는다 [실측]."""

CLAIMS = ("결함이 확인", "확인된 결함", "결함입니다", "버그입니다", "버그를 찾았다")


def _file(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _unlabeled() -> LabeledSample:
    target = ReviewTarget(target_id="t", files=(SourceFile(path="m.py", content="x = 1\n"),))
    return LabeledSample(target=target, stratum=Stratum.UNLABELED)


class TestUnlabeledIsNeverGraded:
    """🔴 결함 라벨이 없다고 음성이 아니다 - 채점하면 지적이 전부 FP 가 된다 (F4)."""

    def test_unlabeled_samples_are_not_graded(self) -> None:
        reviewer = AnalyzerReviewer(create_analyzer("ruff"))
        with pytest.raises(ValueError, match="정답이 없는 샘플은 채점하지 않는다"):
            run_reviewer(reviewer, [_unlabeled()], [ProvableSafetyGrader()])

    def test_an_unlabeled_sample_is_not_a_negative(self) -> None:
        with pytest.raises(ValueError, match="음성인지 모른다"):
            _ = _unlabeled().is_negative


class TestReview:
    def test_a_file_is_reviewed_without_grading(self, tmp_path: Path) -> None:
        report = review_file(_file(tmp_path, "shell.py", SHELL))
        assert [r.split("/")[0] for r in report.reviewers] == ["ruff", "mypy"]
        rules = {e.verified.finding.rule_id for e in report.entries}
        assert {"F401", "S602"} <= rules
        for e in report.entries:
            kinds = {ev.kind for ev in e.verified.evidence}
            # 정적분석기는 파일을 직접 읽어 「인용」이 늘 맞는다 - 근거를 부풀리지 않는다
            assert kinds == {EvidenceKind.CORROBORATION, EvidenceKind.GUARD,
                             EvidenceKind.REACHABILITY}, e.verified.finding.rule_id

    def test_a_reviewer_is_corroborated_only_by_another_tool(self, tmp_path: Path) -> None:
        """🔴 자기 확인은 항등식이다 (F7) - 섞이면 검증자가 실패해 「판단 못 함」으로 숨는다."""
        report = review_file(_file(tmp_path, "both.py", BOTH))
        corroboration = {
            e.reviewer: next(ev for ev in e.verified.evidence
                             if ev.kind is EvidenceKind.CORROBORATION)
            for e in report.entries
        }
        assert set(corroboration) == {"ruff", "mypy"}
        assert all(ev.verdict is Verdict.SUPPORTS for ev in corroboration.values())
        assert "mypy 도" in corroboration["ruff"].detail
        assert "ruff 도" in corroboration["mypy"].detail
        details = [ev.detail for e in report.entries for ev in e.verified.evidence]
        assert not [d for d in details if "검증자가 실패했다" in d]

    def test_the_report_never_claims_a_defect(self, tmp_path: Path) -> None:
        text = render_review(review_file(_file(tmp_path, "shell.py", SHELL)))
        assert "결함을 확인하는 보고서가 아니다" in text
        assert "확률이 아니다" in text
        assert "## 검증자가 보지 못하는 것" in text
        assert [c for c in CLAIMS if c in text] == []

    def test_no_findings_is_not_no_defects(self, tmp_path: Path) -> None:
        text = render_review(review_file(_file(tmp_path, "clean.py", "x: int = 1\n")))
        assert "## 지적 0건" in text
        assert "결함이 없다는 뜻은 아니다" in text


class TestCommand:
    def test_review_prints_the_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(["review", str(_file(tmp_path, "shell.py", SHELL))]) == 0
        out = capsys.readouterr().out
        assert out.startswith("# 리뷰 보고서 — shell.py")
        assert "S602" in out

    def test_review_writes_the_report_to_a_file(self, tmp_path: Path) -> None:
        out = tmp_path / "report.md"
        assert main(["review", str(_file(tmp_path, "shell.py", SHELL)), "--out", str(out)]) == 0
        assert out.read_text(encoding="utf-8").startswith("# 리뷰 보고서")

    @pytest.mark.parametrize("name", ["notes.txt", "missing.py"])
    def test_only_an_existing_python_file_is_reviewed(self, tmp_path: Path, name: str) -> None:
        path = tmp_path / name
        if name.endswith(".txt"):
            path.write_text("x = 1\n", encoding="utf-8")
        assert main(["review", str(path)]) == 2


def _agent_says(monkeypatch: pytest.MonkeyPatch, findings: list[dict[str, object]] | None) -> None:
    """실행기(review-with-agent.sh) 대신 그 출력의 모양을 쓴다 - `<샘플>.0.json` + RUN.json.

    `findings` 가 None 이면 답을 남기지 않은 실행이다.
    """

    def fake(agent: str, src: Path, out: Path) -> None:
        out.mkdir(parents=True)
        record = {"agent": agent, "identity": f"{agent}-code 9.9.9 · m-1 · effort=low"}
        (out / "RUN.json").write_text(json.dumps(record), encoding="utf-8")
        if findings is not None:
            (out / "review.0.json").write_text(json.dumps({"findings": findings}), encoding="utf-8")
        assert (src / "MANIFEST.json").exists()

    monkeypatch.setattr(review, "run_agent", fake)


def _said(path: str, line: int, quote: str) -> dict[str, object]:
    return {
        "file": path, "line_start": line, "line_end": line, "category": "security",
        "severity": "error", "quoted_code": quote, "message": "shell=True 에 외부 입력",
        "failure_mode": "명령 주입",
    }


class TestAgent:
    """🔴 에이전트 지적도 run_reviewer 한 곳으로 돌고, 인용 검증을 받는다 - 지어낸 인용은 0 이다."""

    def test_an_agent_finding_is_verified_with_its_quote(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _file(tmp_path, "shell.py", SHELL)
        _agent_says(monkeypatch, [_said("shell.py", 6, "subprocess.run(cmd, shell=True)")])
        report = review_file(path, agent="claude")
        assert report.reviewers[-1] == "claude-code 9.9.9 · m-1 · effort=low"
        mine = [e for e in report.entries if e.reviewer == "claude"]
        assert len(mine) == 1
        citation = next(ev for ev in mine[0].verified.evidence if ev.kind is EvidenceKind.CITATION)
        assert citation.verdict is Verdict.SUPPORTS
        assert "(정적분석기 + 에이전트)" in render_review(report)

    def test_a_made_up_quote_gets_no_credit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _file(tmp_path, "shell.py", SHELL)
        _agent_says(monkeypatch, [_said("shell.py", 6, "os.system(user_input)")])
        mine = [e for e in review_file(path, agent="claude").entries if e.reviewer == "claude"]
        citation = next(ev for ev in mine[0].verified.evidence if ev.kind is EvidenceKind.CITATION)
        assert citation.verdict is Verdict.REFUTES
        assert mine[0].verified.confidence == 0.0

    def test_a_silent_agent_is_an_error_not_zero_findings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """🔴 답을 남기지 않은 실행을 「지적 0건」으로 접으면 미측정이 미탐지가 된다 (F4)."""
        _agent_says(monkeypatch, None)
        with pytest.raises(ReviewError, match="답을 남기지 않았다"):
            review_file(_file(tmp_path, "shell.py", SHELL), agent="claude")

    def test_the_command_says_why_the_agent_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        _agent_says(monkeypatch, None)
        assert main(["review", str(_file(tmp_path, "shell.py", SHELL)), "--agent", "claude"]) == 1
        assert "답을 남기지 않았다" in capsys.readouterr().err

