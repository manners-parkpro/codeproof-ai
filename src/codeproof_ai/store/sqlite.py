"""SQLite 저장소.

재현성을 설계의 핵심으로 내세웠으면 결과를 보관할 곳이 있어야 한다.
출력되고 사라지면 3개월 뒤 아무것도 확인할 수 없다.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from codeproof_ai.store.schema import DDL, SCHEMA_VERSION

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from codeproof_ai.domain.run import RunManifest
    from codeproof_ai.eval.runner import ReviewerRun


class SchemaVersionError(RuntimeError):
    """디스크의 스키마가 이 코드와 다르다.

    조용히 마이그레이션하지 않는다 - 잘못 읽은 과거 데이터로 결론을 내는 것이
    데이터가 없는 것보다 나쁘다.
    """


@dataclass(frozen=True, slots=True)
class RunRow:
    """저장된 실행의 요약."""

    run_id: str
    config_hash: str
    reviewer: str
    effort: str
    findings: int


@dataclass(frozen=True, slots=True)
class ReproCheck:
    """같은 설정으로 돌린 실행들의 비교 결과."""

    config_hash: str
    runs: tuple[str, ...]
    finding_keys: tuple[frozenset[str], ...]

    @property
    def identical(self) -> bool:
        """모든 실행이 같은 지적 집합을 냈는가."""
        return len(set(self.finding_keys)) <= 1

    @property
    def stable_keys(self) -> frozenset[str]:
        """모든 실행에 공통으로 나온 지적."""
        if not self.finding_keys:
            return frozenset()
        return frozenset.intersection(*self.finding_keys)

    @property
    def volatile_keys(self) -> frozenset[str]:
        """일부 실행에만 나온 지적. 🔴 이게 비결정성의 크기다."""
        if not self.finding_keys:
            return frozenset()
        return frozenset.union(*self.finding_keys) - self.stable_keys


class Store:
    """실행 결과 저장소."""

    def __init__(self, path: Path | str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(DDL)
        self._check_version()

    def _check_version(self) -> None:
        cur = self._conn.execute("SELECT version FROM schema_meta")
        row = cur.fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO schema_meta(version) VALUES (?)", (SCHEMA_VERSION,)
            )
            self._conn.commit()
            return
        if row["version"] != SCHEMA_VERSION:
            msg = (
                f"스키마 버전 불일치: 디스크 {row['version']} vs 코드 {SCHEMA_VERSION}. "
                "조용히 마이그레이션하지 않는다 - 잘못 읽은 과거 데이터로 "
                "결론을 내는 것이 데이터가 없는 것보다 나쁘다."
            )
            raise SchemaVersionError(msg)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── 저장 ────────────────────────────────────────────────

    def save(self, run: ReviewerRun) -> str:
        """실행 하나를 통째로 저장한다.

        🔴 매니페스트가 먼저 들어간다. 외래키 때문에 그것 없이는
           지적도 판정도 들어갈 수 없다 - 구조가 F1 을 강제한다.
        """
        m = run.manifest
        with self._conn:
            self._insert_run(m, run.reviewer)
            for outcome in run.outcomes:
                self._conn.execute(
                    "INSERT OR REPLACE INTO observations"
                    "(run_id, sample_id, reviewer, total_runs, grouper, proven_safe)"
                    " VALUES (?,?,?,?,?,?)",
                    (
                        m.run_id,
                        outcome.sample_id,
                        outcome.observations.reviewer,
                        outcome.observations.total_runs,
                        outcome.observations.grouper,
                        int(outcome.is_proven_safe),
                    ),
                )
                for obs in outcome.observations.observed:
                    self._insert_finding(m.run_id, outcome.sample_id, obs)
                for grader, judgments in outcome.judgments.items():
                    for j in judgments:
                        self._conn.execute(
                            "INSERT OR REPLACE INTO judgments"
                            "(run_id, sample_id, finding_key, grader, outcome,"
                            " matched_defect, rationale) VALUES (?,?,?,?,?,?,?)",
                            (
                                m.run_id,
                                outcome.sample_id,
                                j.finding_key,
                                grader,
                                j.outcome.value,
                                j.matched_defect,
                                j.rationale,
                            ),
                        )
        return m.run_id

    def _insert_run(self, m: RunManifest, reviewer: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs(run_id, config_hash, reviewer, model_id,"
            " prompt_hash, corpus_hash, effort, sample_n, cache_policy, grouper,"
            " harness_sha, client_region, created_at, params_sent, params_omitted,"
            " tool_versions) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                m.run_id,
                m.config_hash,
                reviewer,
                m.model_id,
                m.prompt_hash,
                m.corpus_hash,
                m.effort,
                m.sample_n,
                m.cache_policy,
                m.grouper,
                m.harness_sha,
                m.client_region,
                m.created_at.isoformat(),
                json.dumps(m.params_sent, sort_keys=True, default=str),
                json.dumps(list(m.params_omitted)),
                json.dumps([[t.name, t.version] for t in m.tool_versions]),
            ),
        )

    def _insert_finding(self, run_id: str, sample_id: str, obs: Any) -> None:
        f = obs.finding
        loc = f.location
        self._conn.execute(
            "INSERT OR REPLACE INTO findings(run_id, sample_id, finding_key, source,"
            " rule_id, rule_name, category, severity, message, hint, path,"
            " line_start, line_end, col_char, col_byte, symbol, quoted_code,"
            " suppression, occurred_in, total_runs, raw)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                sample_id,
                f.fingerprint,
                f.source,
                f.rule_id,
                f.rule_name,
                f.category.value,
                f.severity.value,
                f.message,
                f.hint,
                loc.path,
                loc.span.start.line,
                loc.span.end.line if loc.span.end else None,
                loc.span.start.column,
                loc.span.start.byte_column,
                loc.symbol,
                f.quoted_code,
                f.suppression,
                json.dumps(sorted(obs.runs)),
                obs.total_runs,
                json.dumps(f.raw, default=str),
            ),
        )

    # ── 조회 ────────────────────────────────────────────────

    def runs(self, limit: int = 50) -> list[RunRow]:
        cur = self._conn.execute(
            "SELECT r.*, (SELECT COUNT(*) FROM findings f WHERE f.run_id = r.run_id)"
            " AS n FROM runs r ORDER BY r.created_at DESC LIMIT ?",
            (limit,),
        )
        return [
            RunRow(
                run_id=row["run_id"],
                config_hash=row["config_hash"],
                reviewer=row["reviewer"],
                effort=row["effort"],
                findings=row["n"],
            )
            for row in cur
        ]

    def finding_keys(self, run_id: str) -> frozenset[str]:
        cur = self._conn.execute(
            "SELECT sample_id, finding_key FROM findings WHERE run_id = ?", (run_id,)
        )
        return frozenset(f"{r['sample_id']}::{r['finding_key']}" for r in cur)

    def repro_check(self, config_hash: str) -> ReproCheck:
        """같은 설정으로 돌린 실행들을 비교한다.

        🔴 해석은 리뷰어 종류에 달려 있다:
           정적분석기 - 다르면 **재현돼야 할 것이 안 된 것** (도구·환경 드리프트)
           모델      - 다른 게 정상. 그 폭이 곧 측정 대상
        """
        cur = self._conn.execute(
            "SELECT run_id FROM runs WHERE config_hash = ? ORDER BY created_at",
            (config_hash,),
        )
        ids = tuple(r["run_id"] for r in cur)
        return ReproCheck(
            config_hash=config_hash,
            runs=ids,
            finding_keys=tuple(self.finding_keys(rid) for rid in ids),
        )

    def judgment_counts(self, run_id: str) -> dict[str, dict[str, int]]:
        """채점자 -> 판정 -> 개수."""
        cur = self._conn.execute(
            "SELECT grader, outcome, COUNT(*) AS n FROM judgments"
            " WHERE run_id = ? GROUP BY grader, outcome",
            (run_id,),
        )
        out: dict[str, dict[str, int]] = {}
        for row in cur:
            out.setdefault(row["grader"], {})[row["outcome"]] = row["n"]
        return out

    def config_hashes(self) -> Iterator[tuple[str, int]]:
        """(설정 지문, 실행 횟수). 2회 이상이면 재현성을 볼 수 있다."""
        cur = self._conn.execute(
            "SELECT config_hash, COUNT(*) AS n FROM runs"
            " GROUP BY config_hash ORDER BY n DESC"
        )
        for row in cur:
            yield row["config_hash"], row["n"]
