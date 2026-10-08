"""정답이 없는 코드의 리뷰 보고서 (`codeproof review`) - 지적과 근거만 내고 채점하지 않는다.

🔴 이 보고서가 「결함 확인」으로 읽히면 이 저장소가 비판하는 오류(증거의 부재를 부재의 증거로)를
   스스로 저지르는 것이다 - 문면과 채점 거부를 둘 다 테스트가 고정한다.
"""

from __future__ import annotations

import json
import re
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
from tests.ollama_fake import FakeOllama

if TYPE_CHECKING:
    from pathlib import Path

SHELL = (
    "import os\nimport subprocess\n\n\n"
    "def run(cmd):\n    return subprocess.run(cmd, shell=True)\n"
)
BOTH = "def f() -> int:\n    return undefined_name\n"
"""Ruff(F821) 와 mypy(name-defined) 가 같은 줄을 짚는다 [실측]."""

CLAIMS = re.compile(
    r"확인(된|한) 결함|결함(이|을)? ?확인(됐|했|되었|하였)|결함입니다|버그입니다|버그를 찾았다"
)
"""결함 확인처럼 읽히는 문구. [실측] 낱말 목록일 때는 「확인한 결함」이 빠져 그 문장을
더해도 통과했다."""


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
        assert not CLAIMS.search(text), CLAIMS.search(text)

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

    def test_an_answer_of_unknown_shape_is_an_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """지적 모양이 아닌 답을 「지적 0건」으로 접지 않는다 (F4) - 깨뜨려도 울던 시험이 없었다."""

        def fake(agent: str, src: Path, out: Path) -> None:  # noqa: ARG001
            out.mkdir(parents=True)
            record = {"agent": agent, "identity": f"{agent}-code 9.9.9 · m-1 · effort=low"}
            (out / "RUN.json").write_text(json.dumps(record), encoding="utf-8")
            (out / "review.0.json").write_text(json.dumps({"result": "산문"}), encoding="utf-8")

        monkeypatch.setattr(review, "run_agent", fake)
        with pytest.raises(ReviewError, match="지적 모양이 아니다"):
            review_file(_file(tmp_path, "shell.py", SHELL), agent="claude")

    def test_agent_findings_get_their_enclosing_function(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """🔴 에이전트 지적도 run_reviewer 한 곳으로 돈다 (E00) - 그래야 둘러싼 함수가 붙는다.

        [실측] run_reviewer 를 건너뛰면 지적이 `<module>` 로 남아 도달성이 「모듈 최상위」로 읽혔다.
        """
        _agent_says(monkeypatch, [_said("shell.py", 6, "subprocess.run(cmd, shell=True)")])
        mine = [e for e in review_file(_file(tmp_path, "shell.py", SHELL), agent="claude").entries
                if e.reviewer == "claude"]
        assert mine[0].verified.finding.location.symbol == "run"

    def test_the_command_says_why_the_agent_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        _agent_says(monkeypatch, None)
        assert main(["review", str(_file(tmp_path, "shell.py", SHELL)), "--agent", "claude"]) == 1
        assert "답을 남기지 않았다" in capsys.readouterr().err



class TestTheReportSaysOnlyWhatItSaw:
    """워크플로 재검증(2026-10-08)이 찾은 결함 - 보고서가 본 것보다 많이 말하지 않는다."""

    def test_a_convention_claim_gets_no_guard_or_reachability(self, tmp_path: Path) -> None:
        """🔴 「줄이 길다」에는 막을 실패가 없다 - 가드로 반박하지 않는다 (F4a)."""
        long_line = "x = 1  # " + "a" * 120 + "\n"
        report = review_file(_file(tmp_path, "style.py", long_line), reviewers=("ruff",))
        style = [e for e in report.entries if e.verified.finding.rule_id == "E501"]
        assert style, "대조군 - E501 이 나와야 이 시험이 공허하지 않다"
        kinds = {ev.kind for ev in style[0].verified.evidence}
        assert EvidenceKind.GUARD not in kinds and EvidenceKind.REACHABILITY not in kinds
        assert "보지 않음 — 관례 주장" in render_review(report)

    def test_findings_on_one_line_are_not_folded(self, tmp_path: Path) -> None:
        """🔴 [실측] `return foo + bar` 의 F821 두 건 중 bar 가 말없이 사라졌다."""
        path = _file(tmp_path, "two.py", "def f() -> int:\n    return foo + bar\n")
        report = review_file(path, reviewers=("ruff",))
        names = sorted(e.verified.finding.message for e in report.entries
                       if e.verified.finding.rule_id == "F821")
        assert len(names) == 2, names
        assert any("bar" in n for n in names) and any("foo" in n for n in names)

    def test_dropped_agent_findings_are_counted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """🔴 버린 지적을 세지 않으면 「짚은 것이 없다」와 구별되지 않는다 (I)."""
        _agent_says(monkeypatch, [_said("other.py", 6, "subprocess.run(cmd, shell=True)")])
        path = _file(tmp_path, "clean.py", "x = 1\n")
        report = review_file(path, reviewers=(), agent="claude")
        assert len(report.rejected) == 1
        text = render_review(report)
        assert "버린 모델 지적 1건" in text
        assert "짚은 것이 없다" not in text

    def test_the_analyzer_settings_are_in_the_report(self, tmp_path: Path) -> None:
        """사용자의 `# noqa` 가 왜 무시되는지 보고서에서 보인다 (F2)."""
        text = render_review(review_file(_file(tmp_path, "a.py", SHELL), reviewers=("ruff",)))
        assert "분석기 설정: `ruff(" in text and "ignore-noqa" in text

    def test_a_bom_does_not_blind_the_verifiers(self, tmp_path: Path) -> None:
        """[실측] BOM 이 남으면 검증자의 파서가 파일 전체를 못 읽고 둘러싼 함수를 잃었다."""
        path = tmp_path / "bom.py"
        path.write_text("﻿" + SHELL, encoding="utf-8")
        report = review_file(path, reviewers=("ruff",))
        s602 = next(e for e in report.entries if e.verified.finding.rule_id == "S602")
        assert s602.verified.finding.location.symbol, "둘러싼 함수를 잃지 않는다"
        assert not any("파싱" in ev.detail for ev in s602.verified.evidence)


class TestCommandGuardsTheUsersFiles:
    def test_the_report_never_overwrites_the_input(self, tmp_path: Path) -> None:
        path = _file(tmp_path, "keep.py", SHELL)
        assert main(["review", str(path), "--out", str(path)]) == 2
        assert path.read_text(encoding="utf-8") == SHELL

    def test_a_missing_report_folder_fails_before_reviewing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """🔴 끝난 뒤에 실패하면 모델 리뷰가 사라진다 - 돌리기 전에 본다."""
        # cli 가 직접 import 한 이름을 바꾼다 - review.review_file 을 바꾸면 감시가 걸리지 않는다
        monkeypatch.setattr("codeproof_ai.cli.review_file", lambda *_, **__: pytest.fail("돌렸다"))
        out = tmp_path / "no" / "such" / "report.md"
        assert main(["review", str(_file(tmp_path, "a.py", SHELL)), "--out", str(out)]) == 2

    def test_a_file_that_is_not_utf8_is_a_clear_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = tmp_path / "latin1.py"
        path.write_bytes("s = 'caf\xe9'\n".encode("latin-1"))
        assert main(["review", str(path)]) == 2
        assert "UTF-8" in capsys.readouterr().err

    def test_an_agent_not_yet_tried_is_not_offered(self) -> None:
        """안 되는 것을 --help 에 두면 쓰는 사람이 속는다 - codex 는 이 경로를 실호출로 안 봤다."""
        assert "codex" not in review.AGENTS
        with pytest.raises(SystemExit):
            main(["review", "x.py", "--agent", "codex"])


class TestLocalModel:
    """🔴 로컬 모델은 에이전트가 아니다 (model_api) - 키 · 계정 없이 로컬 서버를 부른다."""

    def test_a_local_model_review_is_verified_like_any_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with FakeOllama() as fake:
            monkeypatch.setenv("OLLAMA_HOST", fake.host)
            fake.answer = {"findings": [_said("shell.py", 6, "subprocess.run(cmd, shell=True)")]}
            report = review_file(_file(tmp_path, "shell.py", SHELL), local="qwen3:4b")
        mine = [e for e in report.entries if e.reviewer == "ollama"]
        assert len(mine) == 1
        citation = next(ev for ev in mine[0].verified.evidence if ev.kind is EvidenceKind.CITATION)
        assert citation.verdict is Verdict.SUPPORTS
        assert report.reviewers[-1].startswith("ollama qwen3:4b@")
        assert "(정적분석기 + 로컬 모델)" in render_review(report)

    def test_no_local_server_is_an_error_not_zero_findings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
        assert main(["review", str(_file(tmp_path, "a.py", SHELL)), "--ollama", "qwen3:4b"]) == 1
        assert "닿지 않는다" in capsys.readouterr().err
