"""SQLite 스키마.

🔴 매니페스트 없는 결과를 **거부**한다 (CLAUDE.md E1) - 경고가 아니다.
   외래키로 구조가 막는다: 실행 행이 없으면 지적도 판정도 넣을 수 없다.
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final = 1

DDL: Final = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER NOT NULL
);

-- 한 번의 실행. 🔴 모든 것이 여기에 매달린다.
CREATE TABLE IF NOT EXISTS runs (
    run_id         TEXT PRIMARY KEY,
    config_hash    TEXT NOT NULL,   -- 시각을 뺀 설정 지문
    reviewer       TEXT NOT NULL,
    model_id       TEXT NOT NULL,
    prompt_hash    TEXT NOT NULL,
    corpus_hash    TEXT NOT NULL,
    effort         TEXT NOT NULL,
    sample_n       INTEGER NOT NULL,
    cache_policy   TEXT NOT NULL,
    grouper        TEXT NOT NULL,
    harness_sha    TEXT NOT NULL,
    client_region  TEXT,
    created_at     TEXT NOT NULL,
    params_sent    TEXT NOT NULL,   -- JSON
    params_omitted TEXT NOT NULL,   -- JSON
    tool_versions  TEXT NOT NULL    -- JSON
);

CREATE INDEX IF NOT EXISTS idx_runs_config ON runs(config_hash);

-- 대상별 관측
CREATE TABLE IF NOT EXISTS observations (
    run_id      TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    sample_id   TEXT NOT NULL,
    reviewer    TEXT NOT NULL,
    total_runs  INTEGER NOT NULL,
    grouper     TEXT NOT NULL,
    proven_safe INTEGER NOT NULL,
    PRIMARY KEY (run_id, sample_id)
);

-- 관측된 고유 지적. runs 는 등장한 실행 번호 집합 (JSON) 이다 - 개수가 아니다.
CREATE TABLE IF NOT EXISTS findings (
    run_id       TEXT NOT NULL,
    sample_id    TEXT NOT NULL,
    finding_key  TEXT NOT NULL,
    source       TEXT NOT NULL,
    rule_id      TEXT NOT NULL,
    rule_name    TEXT,
    category     TEXT NOT NULL,
    severity     TEXT NOT NULL,
    message      TEXT NOT NULL,
    hint         TEXT,
    path         TEXT NOT NULL,
    line_start   INTEGER NOT NULL,
    line_end     INTEGER,
    col_char     INTEGER NOT NULL,
    col_byte     INTEGER,
    symbol       TEXT,
    quoted_code  TEXT,
    suppression  TEXT,
    occurred_in  TEXT NOT NULL,   -- JSON: 등장한 실행 번호 집합
    total_runs   INTEGER NOT NULL,
    raw          TEXT NOT NULL,   -- JSON: 🔴 도구 원본. 정규화가 틀렸을 때의 유일한 근거
    PRIMARY KEY (run_id, sample_id, finding_key),
    FOREIGN KEY (run_id, sample_id)
        REFERENCES observations(run_id, sample_id) ON DELETE CASCADE
);

-- 채점 결과. 고유 지적 하나당 채점자 하나씩.
CREATE TABLE IF NOT EXISTS judgments (
    run_id         TEXT NOT NULL,
    sample_id      TEXT NOT NULL,
    finding_key    TEXT NOT NULL,
    grader         TEXT NOT NULL,
    outcome        TEXT NOT NULL,
    matched_defect TEXT,
    rationale      TEXT NOT NULL,
    PRIMARY KEY (run_id, sample_id, finding_key, grader),
    FOREIGN KEY (run_id, sample_id, finding_key)
        REFERENCES findings(run_id, sample_id, finding_key) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_judgments_grader ON judgments(run_id, grader);
"""
