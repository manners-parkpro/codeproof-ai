"""통합 Reviewer - 지적을 내는 모든 것이 같은 하네스로 돈다.

🔴 이 재편성의 핵심 주장: **API 키 없이도 리뷰어를 추가할 수 있다.**
   SARIF 를 내는 도구, 에이전트 CLI 출력, 사람 리뷰가 전부 들어온다.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from codeproof_ai.analysis.python.ruff import RuffAnalyzer
from codeproof_ai.domain.reviewer import Reviewer, ReviewerKind
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.eval.pairing import discrimination_rate, pair_summary, score_pairs
from codeproof_ai.eval.runner import run_reviewer
from codeproof_ai.llm.replay import ReplayProvider
from codeproof_ai.reviewers.imported import ImportedReviewer
from codeproof_ai.reviewers.wrap import AnalyzerReviewer, ProviderReviewer

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


@pytest.fixture(scope="module")
def sarif_dir() -> Path:
    """실제 Ruff SARIF 를 만든다 - 합성 픽스처가 아니라 진짜 출력이어야
    파서가 실물과 맞는지 알 수 있다."""
    out = Path(tempfile.mkdtemp(prefix="cp-sarif-"))
    for s in load_decoy_samples(DECOYS):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for f in s.target.files:
                (root / f.path).write_text(f.content, encoding="utf-8")
            r = subprocess.run(
                [
                    "uv", "run", "ruff", "check", str(root),
                    "--output-format=sarif", "--no-cache", "--exit-zero",
                    "--isolated", "--ignore-noqa", "--select=S,B,F,SIM",
                ],
                capture_output=True, text=True, check=False,
            )
            (out / f"{s.sample_id}.json").write_text(r.stdout or "{}", encoding="utf-8")
    return out


class TestReviewerProtocol:
    def test_wrapped_analyzer_is_a_reviewer(self) -> None:
        assert isinstance(AnalyzerReviewer(RuffAnalyzer()), Reviewer)

    def test_wrapped_provider_is_a_reviewer(self) -> None:
        r = ProviderReviewer(ReplayProvider(), effort="low")
        assert isinstance(r, Reviewer)

    def test_imported_is_a_reviewer(self, tmp_path: Path) -> None:
        r = ImportedReviewer(tmp_path, name="x", identity="v1")
        assert isinstance(r, Reviewer)

    def test_kinds_are_distinct(self, tmp_path: Path) -> None:
        """🔴 층이 다르면 섞어 집계하면 안 된다 - 타입이 그 경계를 표현한다."""
        assert AnalyzerReviewer(RuffAnalyzer()).kind is ReviewerKind.STATIC
        assert ProviderReviewer(ReplayProvider(), effort="low").kind is ReviewerKind.MODEL_API
        assert ImportedReviewer(tmp_path, name="x", identity="v").kind is ReviewerKind.IMPORTED

    def test_provider_requires_effort(self) -> None:
        with pytest.raises(ValueError, match="effort"):
            ProviderReviewer(ReplayProvider(), effort="")


class TestDeterminismGuard:
    """🔴 결정적 리뷰어를 N번 돌려 세면 출현 빈도가 의미를 잃는다."""

    def test_repeating_a_deterministic_reviewer_is_refused(self) -> None:
        samples = load_decoy_samples(DECOYS)[:2]
        with pytest.raises(ValueError, match="결정적"):
            run_reviewer(
                AnalyzerReviewer(RuffAnalyzer()), samples, [], sample_n=8
            )

    def test_single_run_is_fine(self) -> None:
        samples = load_decoy_samples(DECOYS)[:2]
        run = run_reviewer(AnalyzerReviewer(RuffAnalyzer()), samples, [], sample_n=1)
        assert len(run.outcomes) == 2

    def test_stochastic_reviewer_may_repeat(self) -> None:
        samples = load_decoy_samples(DECOYS)[:2]
        run = run_reviewer(
            ProviderReviewer(ReplayProvider(), effort="low"), samples, [], sample_n=4
        )
        assert run.manifest.sample_n == 4
        assert all(o.observations.total_runs == 4 for o in run.outcomes)


class TestSarifImport:
    """🔴 이게 되면 SARIF 를 내는 모든 도구가 리뷰어가 된다 - 자격증명 없이."""

    def test_import_matches_direct_execution(self, sarif_dir: Path) -> None:
        """가져온 결과가 직접 실행과 같아야 경로가 옳다."""
        samples = load_decoy_samples(DECOYS)
        graders = [ProvableSafetyGrader()]

        direct = run_reviewer(
            AnalyzerReviewer(RuffAnalyzer(select=("S", "B", "F", "SIM"))),
            samples, graders,
        )
        imported = run_reviewer(
            ImportedReviewer(sarif_dir, name="ruff-sarif", identity="ruff/sarif"),
            samples, graders,
        )

        d_hit, d_total = discrimination_rate(score_pairs(direct.outcomes, "provable_safety"))
        i_hit, i_total = discrimination_rate(score_pairs(imported.outcomes, "provable_safety"))
        assert (d_hit, d_total) == (i_hit, i_total)

        d_counts = pair_summary(score_pairs(direct.outcomes, "provable_safety"))
        i_counts = pair_summary(score_pairs(imported.outcomes, "provable_safety"))
        assert d_counts == i_counts, "가져온 결과가 직접 실행과 다르다 - 파서가 틀렸다"

    def test_sarif_columns_are_normalized(self, sarif_dir: Path) -> None:
        """SARIF 는 1-based 문자 - 내부 규약은 0-based (B1)."""
        samples = load_decoy_samples(DECOYS)
        run = run_reviewer(
            ImportedReviewer(sarif_dir, name="s", identity="v"), samples, []
        )
        for o in run.outcomes:
            for ob in o.observations.observed:
                assert ob.finding.location.span.start.column >= 0

    def test_missing_file_yields_nothing_not_an_error(self, tmp_path: Path) -> None:
        """🔴 없는 것은 「지적 0건」이다. 예외로 실행을 멈추지 않는다."""
        samples = load_decoy_samples(DECOYS)[:1]
        run = run_reviewer(
            ImportedReviewer(tmp_path, name="empty", identity="v"), samples, []
        )
        assert run.total_findings == 0

    def test_findings_outside_the_target_are_dropped(self, tmp_path: Path) -> None:
        """제시되지 않은 파일을 가리키는 지적은 환각이다 - 버리고 기록한다."""
        samples = load_decoy_samples(DECOYS)[:1]
        sid = samples[0].sample_id
        (tmp_path / f"{sid}.json").write_text(
            json.dumps({
                "runs": [{
                    "tool": {"driver": {"name": "fake", "rules": []}},
                    "results": [{
                        "ruleId": "X1",
                        "level": "error",
                        "message": {"text": "ghost"},
                        "locations": [{"physicalLocation": {
                            "artifactLocation": {"uri": "nowhere.py"},
                            "region": {"startLine": 1, "startColumn": 1},
                        }}],
                    }],
                }]
            }),
            encoding="utf-8",
        )
        run = run_reviewer(
            ImportedReviewer(tmp_path, name="fake", identity="v"), samples, []
        )
        assert run.total_findings == 0


class TestAgentKindIsLabelled:
    """🔴 에이전트는 툴 접근·다회 턴이 가능해서 model_api 와 층이 다르다."""

    def test_agent_kind_is_preserved(self, tmp_path: Path) -> None:
        r = ImportedReviewer(
            tmp_path, name="codex-cli", identity="0.155.1", kind=ReviewerKind.AGENT
        )
        assert r.kind is ReviewerKind.AGENT
        assert "agent" in r.config_signature()

    def test_agent_is_deterministic_only_as_a_recording(self, tmp_path: Path) -> None:
        """가져온 에이전트 출력은 **재생**이므로 결정적이다 -
        원래 실행이 확률적이었다는 것과 별개다."""
        r = ImportedReviewer(
            tmp_path, name="a", identity="v", kind=ReviewerKind.AGENT
        )
        assert not r.kind.is_deterministic, "AGENT 는 확률적 층으로 표시된다"

    def test_manifest_records_the_kind(self, tmp_path: Path) -> None:
        samples = load_decoy_samples(DECOYS)[:1]
        run = run_reviewer(
            ImportedReviewer(tmp_path, name="a", identity="v"), samples, []
        )
        assert run.manifest.params_sent["reviewer_kind"] == "imported"
