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
from typing import Any

import pytest

from codeproof_ai.cli import main
from codeproof_ai.eval.loader import PRESENTED_FILENAME
from codeproof_ai.reviewers.imported import BUNDLE_FILE, RUN_FILE, pack_runs
from codeproof_ai.store.sqlite import Store

ROOT = Path(__file__).resolve().parents[2]
DECOYS = ROOT / "corpus" / "decoys"


@pytest.fixture
def db(tmp_path: Path) -> str:
    return str(tmp_path / "t.db")


def _runner_output(
    root: Path,
    corpus: Path,
    runs: int,
    short: str | None = None,
    *,
    agent: str = "claude",
    docstrings: str = "keep",
    cli_version: str = "9.9.9",
) -> Path:
    """실행기(review-with-agent.sh) 출력의 모양 - `<샘플>.<회차>.json` + RUN.json.

    `short` 샘플만 한 회차 모자라게 쓴다.
    """
    src = root / "runner"
    src.mkdir()
    finding = {"findings": [{
        "file": PRESENTED_FILENAME, "line_start": 1, "line_end": 1,
        "category": "correctness", "severity": "error", "quoted_code": "x",
        "message": "m", "failure_mode": "f",
    }]}
    for d in corpus.iterdir():
        for sid in (d.name, f"{d.name}#twin"):
            for i in range(runs - 1 if sid == short else runs):
                (src / f"{sid}.{i}.json").write_text(json.dumps(finding), encoding="utf-8")
    run = {
        "agent": agent, "cli_version": cli_version, "model": "m-1", "effort": "low",
        "identity": "claude-code 9.9.9 · m-1 · effort=low", "prompt_hash": "p" * 24,
        "docstrings": docstrings,
    }
    (src / RUN_FILE).write_text(json.dumps(run), encoding="utf-8")
    return src


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
    def _sarif(self, uri: str = PRESENTED_FILENAME) -> dict[str, object]:
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
                                        "artifactLocation": {"uri": uri},
                                        "region": {"startLine": 1, "startColumn": 1},
                                    }
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    def _write_pair(self, tmp_path: Path, uri: str = PRESENTED_FILENAME) -> Path:
        """짝의 **양쪽**을 채운다 - 반쪽만 두면 짝 채점이 성립하지 않는다."""
        src = tmp_path / "out"
        src.mkdir(exist_ok=True)
        sid = "D001-upstream-validated-dict-access"
        for name in (sid, f"{sid}#twin"):
            (src / f"{name}.json").write_text(
                json.dumps(self._sarif(uri)), encoding="utf-8"
            )
        return src

    def test_imports_external_findings(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = self._write_pair(tmp_path)
        code = main(
            [
                "import", "--from", str(src), "--name", "fake",
                "--identity", "v1", "--store", db, "--allow-partial",
            ]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "fake" in out
        # 🔴 exit 0 만 보면 약하다 - 지적이 실제로 들어왔는지 본다.
        #    [실측] 제시 파일명이 바뀌었을 때 이 단언이 없었으면
        #    지적이 전부 버려진 채로 통과했을 것이다.
        assert "지적 1건" in out, f"가져온 지적이 없다:\n{out}"

    def test_sarif_findings_on_other_paths_are_counted(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 경로가 어긋난 SARIF 는 전부 버려진다 - 세지 않으면 exit 0 · 경고 0 · 「지적 0건」이다.

        [실측] 그렇게 들어왔다 - 버린 지적은 native 만 셌다.
        대조군은 바로 위 test_imports_external_findings (경로가 맞으면 지적이 들어온다).
        """
        src = self._write_pair(tmp_path, uri="elsewhere.py")
        code = main(
            [
                "import", "--from", str(src), "--name", "fake",
                "--identity", "v1", "--store", db, "--allow-partial",
            ]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "파서가 버린 지적 2건" in out, f"버린 지적이 보이지 않는다:\n{out}"
        assert "elsewhere.py" in out

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
        src = self._write_pair(tmp_path)
        main(
            [
                "import", "--from", str(src), "--name", "codex-cli",
                "--identity", "0.1", "--kind", "agent", "--store", db,
                "--allow-partial",
            ]
        )
        assert "섞어서 집계하지 않는다" in capsys.readouterr().out

    def test_partial_coverage_is_refused_by_default(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 결과가 없는 샘플은 「지적 0건」으로 들어온다 - 미측정이 미탐지가 된다.

        [실측] 120개 중 2개만 채우고 집계했더니 `P-B 미탐지 60` 이 나왔다.
        한 쌍만 측정했는데 60쌍을 놓친 것처럼 보인다 - 증거의 부재를
        오답으로 세는 F4 와 같은 종류다.
        """
        src = self._write_pair(tmp_path)
        code = main(
            [
                "import", "--from", str(src), "--name", "fake",
                "--identity", "v1", "--store", db,
            ]
        )
        assert code == 2
        assert "미측정이 미탐지로 둔갑" in capsys.readouterr().err

    def test_partial_coverage_scores_only_complete_pairs(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--allow-partial 이어도 **측정된 짝만** 센다 - 경고만으로는 부족하다."""
        src = self._write_pair(tmp_path)
        main(
            [
                "import", "--from", str(src), "--name", "fake",
                "--identity", "v1", "--store", db, "--allow-partial",
            ]
        )
        cap = capsys.readouterr()
        assert "완전한 짝 1쌍만 집계한다" in cap.err
        assert "/1" in cap.out, "짝 수가 코퍼스 전체로 부풀었다"

    def _write_agent_run(self, tmp_path: Path) -> Path:
        """실행기(review-with-agent.sh) 출력의 모양 - native 지적 + RUN.json."""
        src = tmp_path / "agent"
        src.mkdir(exist_ok=True)
        sid = "D001-upstream-validated-dict-access"
        finding = {
            "file": PRESENTED_FILENAME, "line_start": 1, "line_end": 1,
            "category": "correctness", "severity": "error", "quoted_code": "x",
            "message": "planted", "failure_mode": "f",
        }
        for name in (sid, f"{sid}#twin"):
            (src / f"{name}.0.json").write_text(
                json.dumps({"findings": [finding]}), encoding="utf-8"
            )
        run = {
            "agent": "claude", "cli_version": "9.9.9", "model": "m-1", "effort": "low",
            "identity": "claude-code 9.9.9 · m-1 · effort=low", "prompt_hash": "p" * 24,
        }
        (src / "RUN.json").write_text(json.dumps(run), encoding="utf-8")
        return src

    def _import_agent(self, src: Path, db: str, *extra: str) -> int:
        return main(
            [
                "import", "--from", str(src), "--name", "claude-code",
                "--kind", "agent", "--store", db, "--allow-partial", *extra,
            ]
        )

    def test_run_record_is_the_manifest(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 E01 - 러너의 정적 도구용 기본값(effort=n/a(static))이 실리면 안 된다.

        에이전트는 effort 를 받고 돌았다. 기록이 있으면 리뷰어가 그대로 신고한다.
        """
        src = self._write_agent_run(tmp_path)
        assert self._import_agent(src, db) == 0
        out = capsys.readouterr().out
        assert "effort        : low" in out
        # 에이전트 CLI 는 캐시를 끌 수단이 없다 - nonce 도 cold_only 도 거짓이다.
        assert "cache_policy  : uncontrolled" in out
        assert "claude-cli==9.9.9" in out
        assert f"prompt_hash   : {'p' * 24}" in out
        assert "claude-code 9.9.9 · m-1 · effort=low" in out, "identity 를 기록에서 읽지 않았다"
        # 🔴 포맷을 안 줬다 - 기록이 있으면 native 로 읽어야 지적이 들어온다.
        assert "고유 1건" in out, f"지적이 들어오지 않았다:\n{out}"

    def test_identity_contradicting_the_record_is_refused(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """[실측] 커밋 메시지 예시의 `--identity 2.1.250` 은 다음 날 실제와 달랐다."""
        src = self._write_agent_run(tmp_path)
        assert self._import_agent(src, db, "--identity", "claude-code 2.1.250") == 2
        assert "실행 기록과 다르다" in capsys.readouterr().err

    def test_matching_identity_is_accepted(self, tmp_path: Path, db: str) -> None:
        src = self._write_agent_run(tmp_path)
        code = self._import_agent(src, db, "--identity", "claude-code 9.9.9 · m-1 · effort=low")
        assert code == 0

    def test_wrong_format_is_not_read_as_zero_findings(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 native 출력을 sarif 로 읽으면 파서는 예외 없이 「지적 0건」을 낸다.

        그러면 전 샘플이 미탐지(P-B)로 채점된다. 저장하지 않고 거부한다.
        """
        src = self._write_agent_run(tmp_path)
        assert self._import_agent(src, db, "--format", "sarif") == 2
        assert "모양이 아닌 파일" in capsys.readouterr().err

    def test_rejected_findings_are_counted(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """제시되지 않은 파일을 가리킨 지적은 버려진다 - 미탐지와 구별이 안 되므로 센다."""
        src = self._write_agent_run(tmp_path)
        bad = {"findings": [{"file": "./elsewhere.py", "line_start": 1, "line_end": 1,
                             "category": "correctness", "severity": "error",
                             "quoted_code": "x", "message": "m", "failure_mode": "f"}]}
        (src / "D001-upstream-validated-dict-access#twin.0.json").write_text(
            json.dumps(bad), encoding="utf-8"
        )
        assert self._import_agent(src, db) == 0
        assert "파서가 버린 지적 1건" in capsys.readouterr().out

    def _write_runs(self, tmp_path: Path, runs: dict[str, int]) -> Path:
        """샘플별 실행 횟수를 달리해 쓴다 - 다회 실행의 부분 적용을 흉내 낸다."""
        src = self._write_agent_run(tmp_path)
        for f in src.glob("*.0.json"):
            f.unlink()
        finding = {"findings": [{
            "file": PRESENTED_FILENAME, "line_start": 1, "line_end": 1,
            "category": "correctness", "severity": "error", "quoted_code": "x",
            "message": "m", "failure_mode": "f",
        }]}
        for sid, n in runs.items():
            for i in range(n):
                (src / f"{sid}.{i}.json").write_text(json.dumps(finding), encoding="utf-8")
        return src

    def test_short_runs_are_refused_like_missing_ones(
        self, tmp_path: Path, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 8회 중 일부만 있으면 모자란 회차가 「지적 0건」이 된다 - 출현 빈도가 거짓이 된다.

        🔴 모자란 샘플 **하나만** 두고 나머지는 전부 채운다. 결과가 아예 없는 샘플이
           섞이면 그쪽이 먼저 거부해서, 회차 검사를 지워도 이 테스트가 통과한다
           [실측 - falsify.sh short-runs 가 침묵했다].
        """
        short = "D002-shell-true-constant-command#twin"
        full = {f"{d.name}{s}": 2 for d in small_corpus.iterdir() for s in ("", "#twin")}
        src = self._write_runs(tmp_path, full | {short: 1})
        code = main([
            "import", "--from", str(src), "--name", "claude-code",
            "--kind", "agent", "--store", db, "--corpus", str(small_corpus),
        ])
        assert code == 2
        err = capsys.readouterr().err
        assert "2회에 모자란 샘플이 1개다" in err
        assert short in err

    def test_short_runs_drop_their_pair_under_allow_partial(
        self, tmp_path: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        d1, d2 = "D001-upstream-validated-dict-access", "D002-shell-true-constant-command"
        src = self._write_runs(
            tmp_path, {d1: 2, f"{d1}#twin": 2, d2: 2, f"{d2}#twin": 1}
        )
        assert self._import_agent(src, db) == 0
        cap = capsys.readouterr()
        assert "완전한 짝 1쌍만 집계한다" in cap.err
        # 다회 실행은 합집합 한 줄이 아니라 라벨 붙은 관점으로 나온다 (F3 · F6).
        # 🔴 짝 채점 절 안에서 본다 - 민감도 표 머리에도 같은 라벨이 있어서, 출력 전체를 보면
        #    짝 채점이 합집합으로 무너져도 통과한다 [실측 - falsify.sh multirun-labels 가 침묵했다].
        pairs = cap.out.split("[짝 채점 · PrimeVul]", 1)[1].split("[매칭 민감도", 1)[0]
        assert "단일 실행 기대값" in pairs
        assert "k=2 (만장일치)" in pairs

    def test_multirun_sensitivity_is_labeled_by_view(
        self, tmp_path: Path, small_corpus: Path, db: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 다회 실행의 매칭 민감도는 관점마다 낸다 - 라벨 없는 합집합 표가 아니다 (F6).

        [실측] 전에는 `sweep()` 이 관점을 모르고 합집합으로 센 표를 라벨 없이 찍었다 -
        생성물의 k≥1 열과 같은 숫자였다.
        """
        full = {f"{d.name}{s}": 2 for d in small_corpus.iterdir() for s in ("", "#twin")}
        code = main([
            "import", "--from", str(self._write_runs(tmp_path, full)), "--name", "claude-code",
            "--kind", "agent", "--store", db, "--corpus", str(small_corpus),
        ])
        assert code == 0
        section = capsys.readouterr().out.split("[매칭 민감도", 1)[1].split("\n\n", 1)[0]
        assert section.startswith(" · 관점별]"), section
        assert "k≥1 (합집합)" in section
        assert "k=2 (만장일치)" in section
        assert "P-V" not in section, "합집합 분포(P-C/P-V/P-B/P-R)는 1회 실행에서만 낸다"

    def test_half_a_pair_is_not_scored(self, tmp_path: Path, db: str) -> None:
        """🔴 반쪽짜리 짝은 버린다 - 한쪽만으로는 P-C/P-V/P-B/P-R 을 못 가른다 (F5)."""
        src = tmp_path / "half"
        src.mkdir()
        (src / "D001-upstream-validated-dict-access.json").write_text(
            json.dumps(self._sarif()), encoding="utf-8"
        )
        code = main(
            [
                "import", "--from", str(src), "--name", "fake",
                "--identity", "v1", "--store", db, "--allow-partial",
            ]
        )
        assert code == 2


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

    def _agents(self, root: Path, corpus: Path, runs: int, short: str | None = None) -> Path:
        """`results/agent/<이름>/` 의 모양 - 묶음.

        `pack` 을 거치지 않고 묶는다 - 모자란 묶음도 만들어야 report 가 거부하는지 본다.
        """
        src = _runner_output(root, corpus, runs, short)
        dest = root / "agents" / "claude-code"
        dest.mkdir(parents=True)
        shutil.copyfile(src / RUN_FILE, dest / RUN_FILE)
        (dest / BUNDLE_FILE).write_text(pack_runs(src), encoding="utf-8")
        return dest.parent

    def _report(self, corpus: Path, agents: Path, out: Path) -> int:
        return main([
            "report", "--corpus", str(corpus), "--agents", str(agents), "--out", str(out),
        ])

    def test_agent_runs_get_a_labeled_section(self, small_corpus: Path, tmp_path: Path) -> None:
        """🔴 다회 실행의 모델 숫자는 관점마다 라벨을 붙여 싣는다 - 합집합 한 줄이 아니다 (F6)."""
        agents = self._agents(tmp_path, small_corpus, runs=2)
        a, b = tmp_path / "a.md", tmp_path / "b.md"
        assert self._report(small_corpus, agents, a) == 0
        assert self._report(small_corpus, agents, b) == 0
        body = a.read_text(encoding="utf-8")
        assert body == b.read_text(encoding="utf-8"), "재표집 시드가 고정돼야 최신인지 묻는다"

        section = body.split("## 에이전트 층", 1)[1]
        assert "claude-code 9.9.9 · m-1 · effort=low" in section
        # 🔴 표마다 머리 행을 본다 - 라벨이 절 어딘가에만 있으면 한 표가 합집합 하나로
        #    무너져도 다른 표의 같은 라벨 덕에 통과한다.
        views = "k≥1 (합집합) | k=2 (만장일치)"
        assert f"| 채점자 | 단일 실행 기대값 | 실행별 P-C | {views} |" in section
        assert f"| slack | 단일 실행 기대값 | {views} |" in section
        for g in ("provable_safety", "injected_defect", "paired_fix", "static_corroboration"):
            assert f"| `{g}` |" in section, "구별 성공률은 (리뷰어 x 채점자)의 성질이다"
        assert "run_id" not in section
        assert "created_at" not in section

    def test_two_agents_get_a_paired_comparison(self, small_corpus: Path, tmp_path: Path) -> None:
        """🔴 두 에이전트는 같은 짝 위의 차이로 비교한다 - 두 구간을 눈으로 겹쳐 보지 않는다."""
        agents = tmp_path / "agents"
        for name, agent, runs in (("claude-code", "claude", 2), ("codex-cli", "codex", 1)):
            self._pack(agents, tmp_path, small_corpus, name, runs=runs, agent=agent)
        out = tmp_path / "M.md"
        assert self._report(small_corpus, agents, out) == 0
        section = out.read_text(encoding="utf-8").split("## 에이전트 비교", 1)[1]
        assert "docstring 손잡이 `keep` 에서 **리뷰어만** 다르다." in section
        # 🔴 표마다 머리 행을 본다 - 위 테스트와 같은 이유다.
        assert "| 채점자 | `claude-code` | `codex-cli` | 차이 | 95% 구간 | 판정 |" in section
        assert "| `provable_safety` (주) |" in section
        assert "| slack | 차이 | 95% 구간 | 판정 |" in section
        # 같은 지적을 낸 두 리뷰어다 - 실행 횟수가 달라도 차이는 0 이고 구별되지 않는다.
        assert "| +0.0%p | [+0.0, +0.0]%p | 구별되지 않는다 |" in section

    def _pack(self, agents: Path, root: Path, corpus: Path, name: str, **run: Any) -> None:
        (root / name).mkdir()
        src = _runner_output(root / name, corpus, run.pop("runs", 1), **run)
        dest = agents / name
        dest.mkdir(parents=True)
        shutil.copyfile(src / RUN_FILE, dest / RUN_FILE)
        (dest / BUNDLE_FILE).write_text(pack_runs(src), encoding="utf-8")

    def test_comparisons_vary_one_axis_only(self, small_corpus: Path, tmp_path: Path) -> None:
        """🔴 리뷰어와 docstring 손잡이가 **둘 다** 다른 실행은 비교하지 않는다 (DESIGN §7.10c).

        claude · keep 대 codex · neutral 의 차이에는 두 효과가 섞여 어느 쪽인지 말할 수 없다.
        """
        agents = tmp_path / "agents"
        for name, agent, doc in (
            ("claude-code", "claude", "keep"), ("claude-code-neutral", "claude", "neutral"),
            ("codex-cli", "codex", "keep"), ("codex-cli-neutral", "codex", "neutral"),
        ):
            self._pack(agents, tmp_path, small_corpus, name, agent=agent, docstrings=doc)
        out = tmp_path / "M.md"
        assert self._report(small_corpus, agents, out) == 0
        body = out.read_text(encoding="utf-8")
        compared = {
            line.removeprefix("## 에이전트 비교 — ")
            for line in body.splitlines()
            if line.startswith("## 에이전트 비교")
        }
        assert compared == {
            "`claude-code` vs `claude-code-neutral`",   # 손잡이만
            "`codex-cli` vs `codex-cli-neutral`",       # 손잡이만
            "`claude-code` vs `codex-cli`",             # 리뷰어만 (keep)
            "`claude-code-neutral` vs `codex-cli-neutral`",  # 리뷰어만 (neutral)
        }
        knob = body.split("## 에이전트 비교 — `claude-code` vs `claude-code-neutral`", 1)[1]
        assert "같은 리뷰어에서 **docstring 손잡이만** 다르다 (`keep` · `neutral`)." in knob
        assert "(DESIGN §7.10c)" in knob
        assert "- 손잡이 말고 다른 설정: 없음" in knob.split("\n## ", 1)[0]
        assert "docstring `neutral`" in body, "에이전트 절 머리에 손잡이를 싣는다"

    def test_a_knob_comparison_shows_other_setup_differences(
        self, small_corpus: Path, tmp_path: Path
    ) -> None:
        """🔴 손잡이 말고 다른 설정(CLI 판 등)이 섞이면 그 차이도 손잡이 효과로 읽힌다."""
        agents = tmp_path / "agents"
        self._pack(agents, tmp_path, small_corpus, "claude-code", docstrings="keep")
        self._pack(
            agents, tmp_path, small_corpus, "claude-code-neutral",
            docstrings="neutral", cli_version="9.9.8",
        )
        out = tmp_path / "M.md"
        assert self._report(small_corpus, agents, out) == 0
        assert "- 손잡이 말고 다른 설정: `cli_version` 9.9.9 → 9.9.8" in out.read_text(
            encoding="utf-8"
        )

    def test_one_agent_gets_no_comparison(self, small_corpus: Path, tmp_path: Path) -> None:
        agents = self._agents(tmp_path, small_corpus, runs=2)
        out = tmp_path / "M.md"
        assert self._report(small_corpus, agents, out) == 0
        assert "## 에이전트 비교" not in out.read_text(encoding="utf-8")

    def test_agent_runs_leave_the_static_sections_alone(
        self, small_corpus: Path, tmp_path: Path
    ) -> None:
        """에이전트 절은 덧붙을 뿐이다 - 정적분석기 숫자를 바꾸지 않는다."""
        with_agents, without = tmp_path / "w.md", tmp_path / "wo.md"
        self._report(small_corpus, self._agents(tmp_path, small_corpus, runs=2), with_agents)
        self._report(small_corpus, tmp_path / "none", without)
        plain = without.read_text(encoding="utf-8")
        assert "## 에이전트 층" not in plain
        assert "**정적분석기**의 것이다" in plain
        static = plain.split("## 이 숫자를 읽는 법")[0]
        assert with_agents.read_text(encoding="utf-8").split("## 에이전트 층")[0] == static

    def test_short_agent_runs_are_refused(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 생성물에 부분 실행을 싣지 않는다 - 모자란 회차가 「지적 0건」으로 실린다 (F6).

        🔴 모자란 샘플 **하나만** 둔다. 결과가 아예 없는 샘플이 섞이면 그쪽이 먼저 거부해서
           회차 검사를 지워도 통과한다 [실측 - falsify.sh short-runs 가 침묵했다].
        """
        short = "D002-shell-true-constant-command#twin"
        out = tmp_path / "M.md"
        code = self._report(
            small_corpus, self._agents(tmp_path, small_corpus, runs=2, short=short), out
        )
        assert code == 2
        err = capsys.readouterr().err
        assert "2회에 모자란 샘플이 1개다" in err
        assert short in err
        assert not out.exists(), "부분 실행으로 쓰면 미측정이 미탐지로 실린다"

    def test_an_unpacked_directory_is_refused(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """실행기 출력을 그대로 두면 묶음이 아니다 - 파일 961개가 다시 커밋되는 길이다."""
        agents = tmp_path / "agents"
        agents.mkdir()
        shutil.copytree(_runner_output(tmp_path, small_corpus, runs=2), agents / "claude-code")
        assert self._report(small_corpus, agents, tmp_path / "M.md") == 2
        assert "codeproof pack" in capsys.readouterr().err


class TestPack:
    """저장소에 싣는 묶음 - 파일 961개 대신 둘. 부분 실행은 묶지 않는다."""

    def _pack(self, corpus: Path, src: Path, out: Path, *extra: str) -> int:
        return main([
            "pack", "--from", str(src), "--out", str(out), "--corpus", str(corpus), *extra,
        ])

    def test_first_runs_packs_only_the_declared_rounds(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 회차가 고르지 않으면 앞 N회만 묶는다 - 묶을 N 은 결과를 보기 전에 정한다.

        [실측] codex 실행은 11샘플만 8회를 가져서, 그대로 묶으면 나머지 109개가
        「모자란 회차」로 거부됐다 (DESIGN §7.10b).
        """
        src = _runner_output(tmp_path, small_corpus, runs=2)
        extra = "D002-shell-true-constant-command#twin"
        for i in (2, 3):
            shutil.copyfile(src / f"{extra}.0.json", src / f"{extra}.{i}.json")
        out = tmp_path / "agents" / "codex-cli"
        assert self._pack(small_corpus, src, out) == 2, "대조 - 그대로 묶으면 거부된다"
        capsys.readouterr()
        assert self._pack(small_corpus, src, out, "--runs", "2") == 0
        bundle = (out / BUNDLE_FILE).read_text(encoding="utf-8").splitlines()
        assert {json.loads(line)["run"] for line in bundle} == {0, 1}, "앞 2회만 묶어야 한다"
        assert json.loads((out / RUN_FILE).read_text(encoding="utf-8"))["packed_runs"] == "2"
        report = tmp_path / "M.md"
        assert main([
            "report", "--corpus", str(small_corpus), "--agents", str(out.parent),
            "--out", str(report),
        ]) == 0
        assert "샘플당 **2회** 실행 (앞 2회만 묶음)" in report.read_text(encoding="utf-8")
        capsys.readouterr()

    def test_first_runs_beyond_what_exists_is_refused(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = tmp_path / "out"
        src = _runner_output(tmp_path, small_corpus, runs=2)
        assert self._pack(small_corpus, src, out, "--runs", "3") == 2
        assert "3회에 모자란 샘플" in capsys.readouterr().err
        assert not out.exists()

    def test_it_writes_two_files_that_report_reads(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = tmp_path / "agents" / "claude-code"
        assert self._pack(small_corpus, _runner_output(tmp_path, small_corpus, runs=2), out) == 0
        assert sorted(p.name for p in out.iterdir()) == sorted([RUN_FILE, BUNDLE_FILE])
        report = tmp_path / "M.md"
        assert main([
            "report", "--corpus", str(small_corpus), "--agents", str(out.parent),
            "--out", str(report),
        ]) == 0
        assert "## 에이전트 층 — `claude-code`" in report.read_text(encoding="utf-8")
        capsys.readouterr()

    def test_pack_refuses_short_runs(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """🔴 모자란 회차는 묶지 않는다 - 묶고 나면 report 에 가서야 걸린다 (F6)."""
        short = "D002-shell-true-constant-command#twin"
        out = tmp_path / "out"
        src = _runner_output(tmp_path, small_corpus, runs=2, short=short)
        assert self._pack(small_corpus, src, out) == 2
        assert "2회에 모자란 샘플이 1개다" in capsys.readouterr().err
        assert not out.exists()

    def test_pack_does_not_mix_with_leftover_files(
        self, small_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """[실측] 묶기 전 이 자리에 실행기 출력 960개가 복사돼 있었다 - 섞이면 그대로 커밋된다."""
        out = tmp_path / "out"
        out.mkdir()
        (out / "D001-upstream-validated-dict-access.0.json").write_text("{}", encoding="utf-8")
        assert self._pack(small_corpus, _runner_output(tmp_path, small_corpus, runs=2), out) == 2
        assert "다른 파일이 있다" in capsys.readouterr().err
        assert not (out / BUNDLE_FILE).exists()
