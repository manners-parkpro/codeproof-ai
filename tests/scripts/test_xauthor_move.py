"""쌍 옮기기 (DESIGN §7.10d) - 실행기 기록 모양의 가짜 1 · 2단계로 고르기 · 복사 · 거절을 본다.

🔴 고르기가 틀리면 조용하다 - 재확인에서 버린 쌍이 섞이거나 한 바퀴를 못 채운 분류가
   들어가도 report 는 분류마다 쌍 수만 센다. 규칙마다 우는 입력을 같이 둔다.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "xauthor_move.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("xauthor_move", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


xm = _load()
COMPLETE = ("bounded_input", "defensive_copy")
SHORT = "frozen_after_init"
"""바퀴 5 를 받아들이지 못한 분류 - 통째로 빠진다."""


def _record(out: Path, n: int, kind: str, rnd: int, outcome: str) -> Path:
    d = out / f"XC{n:03d}"
    pair = d / "final" / f"{d.name}-fake"
    pair.mkdir(parents=True)
    (d / "pair.json").write_text(json.dumps({"kind": kind, "round": rnd}), encoding="utf-8")
    (d / "outcome.json").write_text(json.dumps({"outcome": outcome}), encoding="utf-8")
    for name in xm.xr.PAIR_FILES:
        (pair / name).write_text(f"# {d.name} {name} {outcome}\n", encoding="utf-8")
    (pair / "axes.md").write_text("저자의 메모\n", encoding="utf-8")
    return d


@pytest.fixture
def stages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """1단계 (바퀴 1) + 2단계 (바퀴 2~8) - 버린 쌍 · 못 채운 분류를 섞는다."""
    monkeypatch.setattr(xm, "MIN_KINDS", len(COMPLETE))
    s1, s2 = tmp_path / "stage1", tmp_path / "stage2"
    s1.mkdir()
    s2.mkdir()
    n = 0
    for kind in (*COMPLETE, SHORT):
        n += 1
        _record(s1, n, kind, 1, "accepted")
    for rnd in range(2, 9):
        for kind in (*COMPLETE, SHORT):
            if kind == SHORT and rnd >= 5:
                continue
            if kind == COMPLETE[0] and rnd == 3:
                n += 1
                _record(s2, n, kind, rnd, "failed")  # 재확인에서 버린 쌍
            n += 1
            _record(s2, n, kind, rnd, "accepted" if not (kind == SHORT and rnd == 4) else "failed")
    (s2 / "RUN.json").write_text(json.dumps({"kinds": [*COMPLETE, SHORT]}), encoding="utf-8")
    (s2 / "summary.json").write_text("{}", encoding="utf-8")
    return s1, s2, tmp_path / "corpus" / "codex", tmp_path / "moved.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestSelect:
    def test_each_complete_kind_gets_its_accepted_pair_of_every_round(self, stages: Any) -> None:
        s1, s2, *_ = stages
        chosen = xm.select(s1, s2)
        assert sorted(chosen) == sorted(COMPLETE)
        for records in chosen.values():
            assert [xm.xr.pair_round(d) for d in records] == list(range(1, 9))
            assert {xm.xr.outcome_of(d) for d in records} == {"accepted"}

    def test_a_kind_that_missed_a_round_is_left_out(self, stages: Any) -> None:
        """🔴 한 바퀴를 못 채운 분류는 8쌍이 될 수 없다 - 통째로 뺀다 (선언 「2단계」)."""
        s1, s2, *_ = stages
        assert SHORT not in xm.select(s1, s2)

    def test_fewer_complete_kinds_than_declared_is_incomplete(
        self, stages: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(xm, "MIN_KINDS", len(COMPLETE) + 1)
        s1, s2, *_ = stages
        with pytest.raises(xm.Stop, match="미완"):
            xm.select(s1, s2)

    def test_the_second_stage_must_have_ended(self, stages: Any) -> None:
        """🔴 끝나기 전에는 분류가 바퀴를 채우는 중이다 - 그때 옮기면 구성비가 갈린다 (F5a)."""
        s1, s2, *_ = stages
        (s2 / "summary.json").unlink()
        with pytest.raises(xm.Stop, match="끝나지 않았다"):
            xm.select(s1, s2)


class TestMove:
    def test_only_the_pair_files_are_copied_byte_for_byte(self, stages: Any) -> None:
        s1, s2, target, manifest = stages
        rows = xm.move(xm.select(s1, s2), target, manifest)
        assert len(rows) == 8 * len(COMPLETE)
        for row in rows:
            dest = target / row["pair"]
            assert sorted(p.name for p in dest.iterdir()) == sorted(xm.xr.PAIR_FILES)
            src = s1.parent / row["record"]
            for name in xm.xr.PAIR_FILES:
                original = src / "final" / row["pair"] / name
                assert _sha(dest / name) == _sha(original) == row["files"][name]
        assert json.loads(manifest.read_text(encoding="utf-8"))["pairs"] == rows

    def test_a_corpus_with_pairs_is_not_overwritten(self, stages: Any) -> None:
        s1, s2, target, manifest = stages
        (target / "XC999-kept").mkdir(parents=True)
        with pytest.raises(xm.Stop, match="한 번"):
            xm.move(xm.select(s1, s2), target, manifest)
        assert [p.name for p in target.iterdir()] == ["XC999-kept"]
        assert not manifest.exists()
        assert not target.with_name(f".{target.name}.moving").exists()  # 복사 전에 멈춘다

    def test_check_writes_nothing(self, stages: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        s1, s2, target, manifest = stages
        for name, value in (("STAGE1", s1), ("STAGE2", s2), ("TARGET", target),
                            ("MANIFEST", manifest)):
            monkeypatch.setattr(xm, name, value)
        assert xm.main(["--check"]) == 0
        assert not target.exists() and not manifest.exists()
        assert xm.main([]) == 0
        assert len(xm.corpus_pairs(target)) == 8 * len(COMPLETE)
