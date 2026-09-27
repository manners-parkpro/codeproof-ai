"""CLI — 주 인터페이스의 회귀 방어.

🔴 이 저장소에서 고친 결함 상당수가 CLI 경로에 있었다 (편차 출력 · 짝 채점 ·
   민감도 · 저장 · 자격증명 게이트). 커버리지 25% 로는 회귀를 잡을 수 없다.

원칙: **실제로 돌린다.** 출력 문자열을 단언하되, 문구가 아니라
**그 출력이 나타내는 사실**을 본다 (숫자 · 종료 코드 · 저장 여부).
"""

from __future__ import annotations

import json
import re
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

    def test_measure_succeeds(self, small_corpus: Path, db: str) -> None:
        assert main([
            "measure", "--corpus", str(small_corpus),
            "--analyzers", "ruff", "--store",
            db,
        ]) == 0

    def test_unknown_analyzer_is_rejected(self, small_corpus: Path, db: str) -> None:
        assert main([
            "measure", "--corpus", str(small_corpus),
            "--analyzers", "nope", "--store",
            db,
        ]) == 2

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
        self, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main([
            "measure", "--corpus", str(small_corpus),
            "--analyzers", "ruff", "--ruff-select",
            "ALL", "--store", db,
        ])
        out = capsys.readouterr().out
        for section in ("채점 기준 편차", "짝 채점", "매칭 민감도", "구별 성공"):
            assert section in out, f"'{section}' 절이 사라졌다"

    def test_excludes_non_fp_grader_from_spread(
        self, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 범주 차이를 편차로 오해하지 않는다."""
        main([
            "measure", "--corpus", str(small_corpus),
            "--analyzers", "ruff", "--ruff-select",
            "ALL", "--store", db,
        ])
        out = capsys.readouterr().out
        assert "구조적으로 FP 를 낼 수 없다" in out

    def test_warns_when_negatives_are_too_few(
        self, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["measure", "--corpus", str(small_corpus), "--analyzers", "ruff", "--store", db])
        err = capsys.readouterr().err
        assert "100건 미만" in err, "표본 부족 경고가 사라졌다"

    def test_rule_selection_changes_the_numbers(
        self, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """[실측] 룰 선택만 바꿔도 FP 가 움직인다 - 논지의 핵심.

        🔴 출력이 다르다는 것만으로는 부족하다 - 설정 줄만 달라도 통과한다.
           **FP 수가 실제로 움직였는지**를 본다.
        """
        main([
            "measure", "--corpus", str(small_corpus),
            "--analyzers", "ruff", "--ruff-select", "F", "--store", db,
        ])
        narrow = _fp_counts(capsys.readouterr().out)
        main([
            "measure", "--corpus", str(small_corpus),
            "--analyzers", "ruff", "--ruff-select", "ALL", "--store", db,
        ])
        wide = _fp_counts(capsys.readouterr().out)

        # `--select F` 는 이 표본에서 지적이 0이라 편차 표 자체가 나오지 않는다.
        # 그게 바로 논지다 - 룰 선택 하나로 FP 가 있음/없음으로 갈린다.
        assert wide, "넓은 선택에서도 편차 표가 없다 - 표본이 공허하다 (H2)"
        assert any(v > 0 for v in wide.values()), f"FP 가 0이다: {wide}"
        assert narrow != wide, (
            f"룰 선택이 FP 를 움직이지 않았다: {narrow} vs {wide}"
        )


# 편차 표의 한 줄: "    provable_safety          0    7      231  o"
_SPREAD_ROW = re.compile(r"^\s{4}(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+[ox]\s*$")


def _fp_counts(out: str) -> dict[str, int]:
    """편차 표에서 채점자별 FP 수를 뽑는다.

    🔴 형식이 바뀌면 빈 dict 가 나오고 호출부가 그걸 실패로 본다 -
       조용히 통과하지 않게 한다.
    """
    return {
        m.group(1): int(m.group(3))
        for m in (_SPREAD_ROW.match(line) for line in out.splitlines())
        if m is not None
    }


class TestTheSmallCorpusIsNotVacuous:
    """🔴 배관 시험용 표본이 조용히 비어 버리는 것을 막는다 (H2).

    「지적이 나오는 decoy 를 반드시 포함」이 지켜지지 않으면 위 시험들이
    「둘 다 0건」으로 공허하게 통과한다. 그래서 따로 강제한다.
    """

    def test_it_produces_findings(
        self, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main([
            "measure", "--corpus", str(small_corpus),
            "--analyzers", "ruff", "--ruff-select", "ALL", "--store", db,
        ])
        counts = _fp_counts(capsys.readouterr().out)
        assert counts, "편차 표가 없다"
        assert any(v > 0 for v in counts.values()), (
            f"표본에서 FP 가 하나도 안 나온다: {counts}. "
            "SMALL_CORPUS_PAIRS 에 미끼가 물리는 쌍을 넣어야 한다"
        )


class TestPersistence:
    def test_results_are_stored(self, small_corpus: Path, db: str) -> None:
        main(["measure", "--corpus", str(small_corpus), "--analyzers", "ruff", "--store", db])
        with Store(db) as store:
            runs = store.runs()
        assert len(runs) == 1
        assert runs[0].reviewer == "ruff"

    def test_store_none_skips_and_warns(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["measure", "--corpus", str(small_corpus), "--analyzers", "ruff", "--store", "none"])
        assert "재현할 수 없다" in capsys.readouterr().out
        assert not list(tmp_path.glob("*.db"))

    def test_repeat_run_reports_reproducibility(
        self, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 정적분석기는 같은 설정에서 같은 결과를 내야 한다."""
        main(["measure", "--corpus", str(small_corpus), "--analyzers", "ruff", "--store", db])
        capsys.readouterr()
        main(["measure", "--corpus", str(small_corpus), "--analyzers", "ruff", "--store", db])
        assert "지적 집합 **동일**" in capsys.readouterr().out


class TestHistory:
    def test_lists_stored_runs(
        self, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["measure", "--corpus", str(small_corpus), "--analyzers", "ruff", "--store", db])
        capsys.readouterr()
        assert main(["history", "--store", db]) == 0
        assert "ruff" in capsys.readouterr().out

    def test_empty_store_is_not_an_error(
        self, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["history", "--store", db]) == 0
        assert "없다" in capsys.readouterr().out

    def test_unknown_config_hash_is_rejected(self, small_corpus: Path, db: str) -> None:
        main(["measure", "--corpus", str(small_corpus), "--analyzers", "ruff", "--store", db])
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


class TestReport:
    """🔴 측정값을 **생성**한다 - 문서가 숫자를 베끼면 반드시 낡는다."""

    def test_writes_a_generated_file(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = tmp_path / "M.md"
        assert main(["report", "--corpus", str(small_corpus), "--out", str(out)]) == 0
        body = out.read_text(encoding="utf-8")
        assert "생성된 파일" in body.splitlines()[0]
        assert "codeproof report" in body.splitlines()[0]
        assert "채점 기준 편차" in body
        capsys.readouterr()

    def test_output_is_stable_across_runs(self, small_corpus: Path, tmp_path: Path) -> None:
        """🔴 시각·run_id 를 넣지 않는다 - 넣으면 「최신인가」를 물을 수 없다."""
        a, b = tmp_path / "a.md", tmp_path / "b.md"
        main(["report", "--corpus", str(small_corpus), "--out", str(a)])
        main(["report", "--corpus", str(small_corpus), "--out", str(b)])
        assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")

    def test_it_does_not_change_with_the_harness_commit(
        self, small_corpus: Path, tmp_path: Path
    ) -> None:
        """🔴 생성물은 **내용에 영향 없는 변화**에는 바뀌지 않아야 한다.

        [실측] harness_sha 를 진짜 git SHA 로 고친 직후, 그것이 들어간
        `config_hash` 를 문서에 싣고 있던 탓에 **커밋마다** 이 파일이
        낡은 것으로 잡혔다. 클린 클론에서 `report --check` 가 바로 실패했다.

        그래서 `config_hash`(실행 비교용 DB 키) 대신 `corpus_hash`(샘플 내용
        지문)를 싣는다. 실행 단위 추적은 runs.db 가 한다.
        """
        out = tmp_path / "M.md"
        main(["report", "--corpus", str(small_corpus), "--out", str(out)])
        body = out.read_text(encoding="utf-8")

        assert "config_hash" not in body, (
            "config_hash 에는 harness_sha 가 들어 있어 무관한 커밋마다 달라진다"
        )
        assert "corpus_hash" in body, "무엇으로 만든 숫자인지는 남아야 한다"
        assert "run_id" not in body
        assert "created_at" not in body

    def test_check_detects_a_stale_file(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = tmp_path / "M.md"
        out.write_text("낡은 내용\n", encoding="utf-8")
        assert main(["report", "--corpus", str(small_corpus), "--out", str(out), "--check"]) == 1
        assert "낡았다" in capsys.readouterr().err

    def test_check_passes_on_a_fresh_file(self, small_corpus: Path, tmp_path: Path) -> None:
        out = tmp_path / "M.md"
        main(["report", "--corpus", str(small_corpus), "--out", str(out)])
        assert main(["report", "--corpus", str(small_corpus), "--out", str(out), "--check"]) == 0

    def test_missing_corpus_is_exit_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = str(tmp_path / "none")
        assert main(["report", "--corpus", missing, "--out", "-"]) == 2
        assert "샘플이 없다" in capsys.readouterr().err

    def test_unknown_analyzer_is_exit_2(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main([
            "report", "--corpus", str(small_corpus),
            "--analyzer", "nope", "--out", str(tmp_path / "x.md"),
        ])
        assert code == 2
        capsys.readouterr()
