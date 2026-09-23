"""CLI — 주 인터페이스의 회귀 방어.

🔴 이 저장소에서 고친 결함 상당수가 CLI 경로에 있었다 (편차 출력 · 짝 채점 ·
   민감도 · 저장 · 자격증명 게이트). 커버리지 25% 로는 회귀를 잡을 수 없다.

원칙: **실제로 돌린다.** 출력 문자열을 단언하되, 문구가 아니라
**그 출력이 나타내는 사실**을 본다 (숫자 · 종료 코드 · 저장 여부).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from codeproof_ai.cli import main
from codeproof_ai.store.sqlite import Store

ROOT = Path(__file__).resolve().parents[2]
DECOYS = ROOT / "corpus" / "decoys"


@pytest.fixture
def db(tmp_path: Path) -> str:
    return str(tmp_path / "t.db")


class TestExitCodes:
    """종료 코드는 CI 가 읽는 유일한 신호다."""

    def test_measure_succeeds(self, db: str) -> None:
        assert main(["measure", "--analyzers", "ruff", "--store", db]) == 0

    def test_unknown_analyzer_is_rejected(self, db: str) -> None:
        assert main(["measure", "--analyzers", "nope", "--store", db]) == 2

    def test_unknown_provider_is_rejected(self, db: str) -> None:
        code = main(
            ["eval", "--providers", "nope", "--effort", "low", "--store", db]
        )
        assert code == 2

    def test_missing_corpus_is_rejected(self, db: str) -> None:
        assert main(["measure", "--corpus", "/nowhere", "--store", db]) == 2

    def test_doctor_always_succeeds(self) -> None:
        """자격증명이 없어도 0 이다 - doctor 는 보고지 게이트가 아니다."""
        assert main(["doctor"]) == 0


class TestCredentialGate:
    """🔴 자격증명 없이 모델을 돌리려 하면 막아야 한다."""

    def test_model_provider_without_credentials_fails(
        self, db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "codeproof_ai.llm.credentials._ANTHROPIC_PROFILE_DIR",
            Path("/nonexistent-profile-dir"),
        )
        code = main(
            ["eval", "--providers", "claude", "--effort", "low", "--store", db]
        )
        assert code == 2, "자격증명 없이 통과했다"

    def test_replay_needs_no_credentials(self, db: str) -> None:
        code = main(
            [
                "eval", "--providers", "replay", "--effort", "low",
                "--samples", "2", "--store", db,
            ]
        )
        assert code == 0


class TestMeasureOutput:
    def test_reports_spread_pairing_and_sensitivity(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["measure", "--analyzers", "ruff", "--ruff-select", "ALL", "--store", db])
        out = capsys.readouterr().out
        for section in ("채점 기준 편차", "짝 채점", "매칭 민감도", "구별 성공"):
            assert section in out, f"'{section}' 절이 사라졌다"

    def test_excludes_non_fp_grader_from_spread(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 범주 차이를 편차로 오해하지 않는다."""
        main(["measure", "--analyzers", "ruff", "--ruff-select", "ALL", "--store", db])
        out = capsys.readouterr().out
        assert "구조적으로 FP 를 낼 수 없다" in out

    def test_warns_when_negatives_are_too_few(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["measure", "--analyzers", "ruff", "--store", db])
        err = capsys.readouterr().err
        assert "100건 미만" in err, "표본 부족 경고가 사라졌다"

    def test_rule_selection_changes_the_numbers(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """[실측] 룰 선택만 바꿔도 FP 가 움직인다 - 논지의 핵심."""
        main(["measure", "--analyzers", "ruff", "--ruff-select", "F", "--store", db])
        narrow = capsys.readouterr().out
        main(["measure", "--analyzers", "ruff", "--ruff-select", "ALL", "--store", db])
        wide = capsys.readouterr().out
        assert narrow != wide


class TestPersistence:
    def test_results_are_stored(self, db: str) -> None:
        main(["measure", "--analyzers", "ruff", "--store", db])
        with Store(db) as store:
            runs = store.runs()
        assert len(runs) == 1
        assert runs[0].reviewer == "ruff"

    def test_store_none_skips_and_warns(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["measure", "--analyzers", "ruff", "--store", "none"])
        assert "재현할 수 없다" in capsys.readouterr().out
        assert not list(tmp_path.glob("*.db"))

    def test_repeat_run_reports_reproducibility(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 정적분석기는 같은 설정에서 같은 결과를 내야 한다."""
        main(["measure", "--analyzers", "ruff", "--store", db])
        capsys.readouterr()
        main(["measure", "--analyzers", "ruff", "--store", db])
        assert "지적 집합 **동일**" in capsys.readouterr().out


class TestHistory:
    def test_lists_stored_runs(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["measure", "--analyzers", "ruff", "--store", db])
        capsys.readouterr()
        assert main(["history", "--store", db]) == 0
        assert "ruff" in capsys.readouterr().out

    def test_empty_store_is_not_an_error(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["history", "--store", db]) == 0
        assert "없다" in capsys.readouterr().out

    def test_unknown_config_hash_is_rejected(self, db: str) -> None:
        main(["measure", "--analyzers", "ruff", "--store", db])
        assert main(["history", "--store", db, "--repro", "없는해시"]) == 2


class TestDecoyCommands:
    def test_validate_passes_on_shipped_corpus(self) -> None:
        assert main(["decoy", "validate"]) == 0

    def test_validate_rejects_a_broken_decoy(self, tmp_path: Path) -> None:
        bad = tmp_path / "D999-broken"
        bad.mkdir()
        (bad / "decoy.py").write_text("x = 1\n", encoding="utf-8")
        (bad / "twin.py").write_text("y = 2\n", encoding="utf-8")
        (bad / "meta.toml").write_text('decoy_id = "D999-broken"\n', encoding="utf-8")
        assert main(["decoy", "validate", "--corpus", str(tmp_path)]) == 1

    def test_new_creates_from_template(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        shutil.copytree(DECOYS / "_TEMPLATE", tmp_path / "_TEMPLATE")
        assert main(["decoy", "new", "D900-x", "--corpus", str(tmp_path)]) == 0
        assert (tmp_path / "D900-x" / "meta.toml").is_file()
        assert "D900-x" in (tmp_path / "D900-x" / "meta.toml").read_text(
            encoding="utf-8"
        )
        capsys.readouterr()

    def test_new_refuses_to_overwrite(self, tmp_path: Path) -> None:
        shutil.copytree(DECOYS / "_TEMPLATE", tmp_path / "_TEMPLATE")
        main(["decoy", "new", "D900-x", "--corpus", str(tmp_path)])
        assert main(["decoy", "new", "D900-x", "--corpus", str(tmp_path)]) == 2

    def test_stats_reports_bait_coverage(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["decoy", "stats"]) == 0
        out = capsys.readouterr().out
        assert "시험됨" in out
        assert "trap 분류별" in out


class TestImport:
    def _sarif(self) -> dict[str, object]:
        return {
            "runs": [
                {
                    "tool": {"driver": {"name": "fake", "rules": []}},
                    "results": [
                        {
                            "ruleId": "X1",
                            "level": "error",
                            "message": {"text": "planted"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "decoy.py"},
                                        "region": {"startLine": 1, "startColumn": 1},
                                    }
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    def test_imports_external_findings(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = tmp_path / "out"
        src.mkdir()
        sid = "D001-upstream-validated-dict-access"
        (src / f"{sid}.json").write_text(
            json.dumps(self._sarif()), encoding="utf-8"
        )
        code = main(
            [
                "import", "--from", str(src), "--name", "fake",
                "--identity", "v1", "--store", db,
            ]
        )
        assert code == 0
        assert "fake" in capsys.readouterr().out

    def test_missing_source_directory_is_rejected(self, db: str) -> None:
        code = main(
            [
                "import", "--from", "/nowhere", "--name", "x",
                "--identity", "v", "--store", db,
            ]
        )
        assert code == 2

    def test_empty_source_directory_is_rejected(
        self, tmp_path: Path, db: str
    ) -> None:
        code = main(
            [
                "import", "--from", str(tmp_path), "--name", "x",
                "--identity", "v", "--store", db,
            ]
        )
        assert code == 2

    def test_agent_kind_warns_about_tier(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 에이전트는 model_api 와 층이 다르다 - 섞지 말라고 말해야 한다."""
        src = tmp_path / "out"
        src.mkdir()
        sid = "D001-upstream-validated-dict-access"
        (src / f"{sid}.json").write_text(
            json.dumps(self._sarif()), encoding="utf-8"
        )
        main(
            [
                "import", "--from", str(src), "--name", "codex-cli",
                "--identity", "0.1", "--kind", "agent", "--store", db,
            ]
        )
        assert "섞어서 집계하지 않는다" in capsys.readouterr().out


class TestUnimplementedCommands:
    """🔴 미구현은 조용히 성공하지 않아야 한다."""

    @pytest.mark.parametrize("cmd", ["review", "report"])
    def test_returns_nonzero(
        self, cmd: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = {
            "review": ["review", "--diff", "x", "--provider", "claude", "--effort", "low"],
            "report": ["report", "--run", "x"],
        }[cmd]
        assert main(args) == 1
        assert "미구현" in capsys.readouterr().err
