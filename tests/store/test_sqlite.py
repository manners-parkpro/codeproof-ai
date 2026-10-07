"""저장소 - 재현성의 최소 요건.

🔴 가장 중요한 검사는 **매니페스트 없는 결과가 거부되는가**(F1) 다.
   경고가 아니라 거부여야 하고, 그게 코드가 아니라 **스키마**로 막혀야 한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from codeproof_ai.analysis.python.ruff import RuffAnalyzer
from codeproof_ai.eval.grading.safety import ProvableSafetyGrader
from codeproof_ai.eval.loader import load_decoy_samples
from codeproof_ai.eval.runner import ReviewerRun, run_reviewer
from codeproof_ai.reviewers.wrap import AnalyzerReviewer
from codeproof_ai.store.schema import SCHEMA_VERSION
from codeproof_ai.store.sqlite import SchemaVersionError, Store

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


def _run(select: tuple[str, ...] = ("F", "S")) -> ReviewerRun:
    return run_reviewer(
AnalyzerReviewer(RuffAnalyzer(select=select)),
        load_decoy_samples(DECOYS),
        [ProvableSafetyGrader()],
        harness_sha="test",
    )


class TestManifestIsMandatory:
    """🔴 F1 - 매니페스트 없는 결과는 저장될 수 없다."""

    def test_orphan_observation_is_rejected_by_schema(self, db: Path) -> None:
        with Store(db) as store, pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO observations"
                "(run_id, sample_id, reviewer, total_runs, grouper, proven_safe)"
                " VALUES (?,?,?,?,?,?)",
                ("없는-실행", "s", "ruff", 1, "fingerprint", 1),
            )

    def test_orphan_finding_is_rejected(self, db: Path) -> None:
        with Store(db) as store, pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO findings(run_id, sample_id, finding_key, source,"
                " rule_id, category, severity, message, path, line_start,"
                " col_char, occurred_in, total_runs, raw)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("없는-실행", "s", "k", "ruff", "F401", "correctness",
                 "error", "m", "a.py", 1, 0, "[0]", 1, "{}"),
            )


class TestRoundTrip:
    def test_saves_and_reads_back(self, db: Path) -> None:
        run = _run()
        with Store(db) as store:
            run_id = store.save(run)
            rows = store.runs()
            keys = store.finding_keys(run_id)

        assert len(rows) == 1
        assert rows[0].run_id == run_id
        assert rows[0].reviewer == "ruff"
        assert len(keys) == run.total_findings

    def test_judgments_are_kept(self, db: Path) -> None:
        run = _run()
        with Store(db) as store:
            run_id = store.save(run)
            counts = store.judgment_counts(run_id)
        assert "provable_safety" in counts
        assert sum(counts["provable_safety"].values()) > 0

    def test_saving_twice_is_idempotent(self, db: Path) -> None:
        run = _run()
        with Store(db) as store:
            store.save(run)
            store.save(run)
            assert len(store.runs()) == 1, "같은 run_id 가 두 번 들어갔다"


class TestConfigHashSeparatesSettingsFromTime:
    """🔴 설정 지문은 시각과 무관해야 재현성 비교가 가능하다."""

    def test_same_config_different_time_shares_config_hash(self) -> None:
        a = _run()
        b = _run()
        assert a.manifest.config_hash == b.manifest.config_hash
        assert a.manifest.run_id != b.manifest.run_id

    def test_different_settings_split_the_config_hash(self) -> None:
        assert _run(("F",)).manifest.config_hash != _run(("ALL",)).manifest.config_hash

    def test_manifest_records_config_hash(self) -> None:
        assert _run().manifest.config_hash in _run().manifest.disclosure_block()


class TestReproCheck:
    def test_deterministic_analyzer_reproduces(self, db: Path) -> None:
        """정적분석기는 같은 설정에서 같은 결과를 내야 한다."""
        with Store(db) as store:
            a = _run()
            store.save(a)
            store.save(_run())
            check = store.repro_check(a.manifest.config_hash)

        assert len(check.runs) == 2
        assert check.identical, (
            f"정적분석기가 같은 설정에서 다른 결과를 냈다 - "
            f"변동 {len(check.volatile_keys)}건. 도구 버전이나 환경이 바뀌었다."
        )
        assert check.volatile_keys == frozenset()

    def test_detects_divergence(self, db: Path) -> None:
        """비결정성을 실제로 잡는지 - 잡지 못하면 이 검사는 무의미하다."""
        with Store(db) as store:
            a = _run(("F", "S"))
            store.save(a)

            # 같은 config_hash 를 갖도록 위조하고 지적 하나를 지운다
            b = _run(("F", "S"))
            forged = b.manifest.run_id
            store.save(b)
            store._conn.execute(
                "DELETE FROM findings WHERE run_id = ? AND rowid IN"
                " (SELECT rowid FROM findings WHERE run_id = ? LIMIT 1)",
                (forged, forged),
            )
            store._conn.commit()
            check = store.repro_check(a.manifest.config_hash)

        assert not check.identical, "차이를 잡지 못한다"
        assert len(check.volatile_keys) == 1

    def test_single_run_is_trivially_identical(self, db: Path) -> None:
        with Store(db) as store:
            run = _run()
            store.save(run)
            assert store.repro_check(run.manifest.config_hash).identical

    def test_unknown_config_is_empty(self, db: Path) -> None:
        with Store(db) as store:
            assert store.repro_check("없는해시").runs == ()


class TestSchemaVersion:
    def test_mismatch_refuses_to_open(self, db: Path) -> None:
        """🔴 조용히 마이그레이션하지 않는다 -
        잘못 읽은 과거 데이터로 결론을 내는 게 데이터가 없는 것보다 나쁘다."""
        with Store(db) as store:
            store._conn.execute(
                "UPDATE schema_meta SET version = ?", (SCHEMA_VERSION + 99,)
            )
            store._conn.commit()

        with pytest.raises(SchemaVersionError, match="스키마 버전 불일치"):
            Store(db)

    def test_fresh_db_stamps_version(self, db: Path) -> None:
        with Store(db) as store:
            row = store._conn.execute(
                "SELECT version FROM schema_meta"
            ).fetchone()
        assert row["version"] == SCHEMA_VERSION


class TestRawIsPreserved:
    def test_tool_payload_survives(self, db: Path) -> None:
        """🔴 정규화가 틀렸을 때의 유일한 근거다. 절대 버리지 않는다."""
        run = _run()
        with Store(db) as store:
            run_id = store.save(run)
            row = store._conn.execute(
                "SELECT raw FROM findings WHERE run_id = ? LIMIT 1", (run_id,)
            ).fetchone()
        assert row is not None
        assert row["raw"] not in {"", "{}"}, "도구 원본이 비어 있다"
