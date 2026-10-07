"""codex 저자 실행기 (DESIGN §7.10d) - codex 를 부르지 않는 판정 · 상태 · 프롬프트만 본다.

🔴 판정이 공허하면 크레딧으로 끊긴 세션이 시도로 세어지거나, 재현되지 않은 지적이 쌍을 버리게 한다 -
   판정마다 우는 입력을 같이 둔다.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "xauthor_run.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("xauthor_run", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclass 가 모듈을 sys.modules 에서 찾는다
    spec.loader.exec_module(mod)
    return mod


xr = _load()
CREDIT_MESSAGE = (
    "Your workspace is out of credits. Ask your workspace owner to refill in order to continue."
)
"""codex 0.158.0 이 크레딧이 끊길 때 내는 문장 [실측 · runs/agent/codex-cli-neutral/raw]."""


def _jsonl(path: Path, *events: dict[str, object]) -> Path:
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def _turn(**usage: int) -> dict[str, object]:
    return {"type": "turn.completed", "usage": usage}


class TestReadSession:
    def test_usage_and_turns_are_summed(self, tmp_path: Path) -> None:
        ev = _jsonl(
            tmp_path / "s.jsonl",
            {"type": "thread.started"},
            _turn(input_tokens=100, cached_input_tokens=60, output_tokens=5),
            _turn(
                input_tokens=40, cached_input_tokens=0, output_tokens=7, reasoning_output_tokens=3,
            ),
        )
        s = xr.read_session(ev, tmp_path / "none.err", 0, timed_out=False)
        assert (s.turns, s.cut) == (2, False)
        assert s.usage["input_tokens"] == 140
        assert s.usage["cached_input_tokens"] == 60
        assert s.usage["reasoning_output_tokens"] == 3

    def test_a_credit_cut_in_the_events_is_seen(self, tmp_path: Path) -> None:
        ev = _jsonl(
            tmp_path / "s.jsonl",
            _turn(input_tokens=10),
            {"type": "error", "message": CREDIT_MESSAGE},
            {"type": "turn.failed", "error": {"message": CREDIT_MESSAGE}},
        )
        assert xr.read_session(ev, tmp_path / "none.err", 1, timed_out=False).cut

    def test_a_credit_cut_in_stderr_is_seen(self, tmp_path: Path) -> None:
        err = tmp_path / "s.err"
        err.write_text(f"error: {CREDIT_MESSAGE}\n", encoding="utf-8")
        assert xr.read_session(tmp_path / "none.jsonl", err, 1, timed_out=False).cut

    def test_an_ordinary_failure_is_not_a_credit_cut(self, tmp_path: Path) -> None:
        """대조 - 다른 실패까지 세지 않으면 시간 상한 · 오류로 끊긴 시도가 공짜 재시도가 된다."""
        failed: dict[str, object] = {"type": "turn.failed", "error": {"message": "stream error"}}
        ev = _jsonl(tmp_path / "s.jsonl", failed)
        s = xr.read_session(ev, tmp_path / "none.err", 1, timed_out=True)
        assert (s.cut, s.timed_out) == (False, True)


class TestHarnessProblems:
    @staticmethod
    def _box(tmp_path: Path, pairs: dict[str, str]) -> Path:
        corpus = tmp_path / "box" / "corpus"
        (corpus / "_TEMPLATE").mkdir(parents=True)
        (corpus / "_TEMPLATE" / "meta.toml").write_text('trap_kind = "upstream_validation"\n')
        for name, kind in pairs.items():
            (corpus / name).mkdir()
            (corpus / name / "meta.toml").write_text(f'decoy_id = "{name}"\ntrap_kind = "{kind}"\n')
        return tmp_path / "box"

    def test_one_pair_of_the_assigned_kind_passes(self, tmp_path: Path) -> None:
        box = self._box(tmp_path, {"XC001-bounded": "bounded_input"})
        pair, problems = xr.harness_problems(box, "XC001", "bounded_input")
        assert pair is not None and pair.name == "XC001-bounded"
        assert problems == []

    def test_no_pair_folder_fails(self, tmp_path: Path) -> None:
        """템플릿은 쌍이 아니다 - 그것만 있으면 폴더가 없는 것이다."""
        pair, problems = xr.harness_problems(self._box(tmp_path, {}), "XC001", "bounded_input")
        assert pair is None and problems

    def test_two_pair_folders_fail(self, tmp_path: Path) -> None:
        box = self._box(tmp_path, {"XC001-a": "bounded_input", "XC001-b": "bounded_input"})
        assert xr.harness_problems(box, "XC001", "bounded_input")[1]

    def test_a_different_kind_fails(self, tmp_path: Path) -> None:
        box = self._box(tmp_path, {"XC001-bounded": "defensive_copy"})
        pair, problems = xr.harness_problems(box, "XC001", "bounded_input")
        assert pair is not None
        assert problems and "bounded_input" in problems[0]

    def test_another_pair_id_is_not_mine(self, tmp_path: Path) -> None:
        box = self._box(tmp_path, {"XC002-bounded": "bounded_input"})
        assert xr.harness_problems(box, "XC001", "bounded_input")[0] is None


class TestReproduced:
    @pytest.mark.parametrize(
        ("stdout", "want"),
        [
            ("REPRODUCED\n", True),
            ("trying\nREPRODUCED\n\n", True),
            ("NOT REPRODUCED\n", False),
            ("REPRODUCED\nNOT REPRODUCED\n", False),
            ("REPRODUCED later\n", False),
            ("", False),
        ],
    )
    def test_only_an_exact_last_line_counts(self, stdout: str, want: bool) -> None:
        assert xr.reproduced(stdout) is want


FINDING = {"kind": "false_claim", "lines": "3-5", "summary": "s", "evidence": "e", "repro": "r"}


class TestFindings:

    def _answer(self, tmp_path: Path, data: object) -> Path:
        path = tmp_path / "last.txt"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_a_schema_shaped_answer_is_read(self, tmp_path: Path) -> None:
        found = xr.findings_of(self._answer(tmp_path, {"findings": [FINDING]}))
        assert found == [FINDING]

    def test_no_findings_is_a_valid_answer(self, tmp_path: Path) -> None:
        assert xr.findings_of(self._answer(tmp_path, {"findings": []})) == []

    def test_a_missing_field_is_unreadable(self, tmp_path: Path) -> None:
        broken = {k: v for k, v in FINDING.items() if k != "repro"}
        assert xr.findings_of(self._answer(tmp_path, {"findings": [broken]})) is None

    def test_not_json_is_unreadable(self, tmp_path: Path) -> None:
        path = tmp_path / "last.txt"
        path.write_text("XC001-bounded\n", encoding="utf-8")
        assert xr.findings_of(path) is None
        assert xr.findings_of(tmp_path / "missing.txt") is None


class TestCreditWindows:
    @staticmethod
    def _cuts(out: Path, n: int) -> None:
        out.mkdir(exist_ok=True)
        for _ in range(n):
            with (out / "events.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"event": "credit_cut"}) + "\n")
                f.write(json.dumps({"event": "interrupted"}) + "\n")

    def test_each_credit_cut_ends_a_window(self, tmp_path: Path) -> None:
        """하네스 중단은 창을 끝내지 않는다 - 크레딧 끊김만 센다."""
        self._cuts(tmp_path / "out", 2)
        assert xr.windows_used(tmp_path / "out") == 3

    def test_the_sixth_window_is_used_and_the_seventh_is_not(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        self._cuts(out, 5)
        assert not xr.over_budget(out)
        self._cuts(out, 1)
        assert xr.over_budget(out)


class TestPrompts:
    def test_the_first_attempt_has_no_gate_output(self) -> None:
        task = xr.task_write("XC001", "bounded_input", 1, None)
        assert "`XC001`" in task and "`bounded_input`" in task
        assert "```" not in task

    def test_a_later_attempt_carries_the_gate_output_verbatim(self) -> None:
        gate_out = "XC001-bounded\n  ✗  mutants  「한도 뺌」 (약화) 깨짐 0/1\n\n관문 1쌍 · 통과 0"
        task = xr.task_write("XC001", "bounded_input", 2, gate_out)
        assert gate_out in task
        assert f"2/{xr.ATTEMPTS}" in task

    def test_the_fix_task_carries_every_problem_and_its_output(self) -> None:
        problems = [
            {"kind": "false_claim", "lines": "7", "summary": "음수 한도", "evidence": "e1",
             "repro": "import decoy\nprint('REPRODUCED')", "stdout_tail": "REPRODUCED"},
            {"kind": "claim_overstated", "lines": "9-12", "summary": "빈 입력", "evidence": "e2",
             "repro": "print('REPRODUCED')", "stdout_tail": "x\nREPRODUCED"},
        ]
        task = xr.task_fix("XC001", "bounded_input", problems)
        for p in problems:
            assert p["summary"] in task and p["repro"] in task and p["stdout_tail"] in task
        assert "### 문제 2" in task
        assert "response.md" in task

    def test_the_fixed_documents_are_the_committed_ones(self) -> None:
        """🔴 수집 전에 커밋하고 바꾸지 않는다 (선언 「쓰는 입력」) - 바꾸면 상수도 바뀐다."""
        for path, want in ((xr.PROMPT, xr.PROMPT_SHA256), (xr.AUDIT_HEAD, xr.AUDIT_HEAD_SHA256)):
            assert hashlib.sha256(path.read_bytes()).hexdigest() == want, path.name


class TestAbandon:
    @staticmethod
    def _session_files(d: Path, step: str) -> None:
        for suffix in ("prompt.txt", "jsonl", "err"):
            (d / f"{step}.{suffix}").write_text(suffix, encoding="utf-8")

    def test_a_cut_session_is_set_aside_and_the_box_restored(self, tmp_path: Path) -> None:
        d, box, snap = tmp_path / "XC001", tmp_path / "box", tmp_path / "snap"
        d.mkdir()
        (box / "corpus").mkdir(parents=True)
        (box / "corpus" / "a.txt").write_text("before", encoding="utf-8")
        xr.snapshot(box, snap)
        (box / "corpus" / "a.txt").write_text("after", encoding="utf-8")
        (box / "corpus" / "b.txt").write_text("new", encoding="utf-8")
        self._session_files(d, "write-1")
        xr.abandon(d, "write-1", "credits", box, snap)
        assert not list(d.glob("write-1.*"))
        assert (d / "cut" / "01-write-1.jsonl").exists()
        assert (d / "cut" / "01-write-1.reason").read_text(encoding="utf-8").strip() == "credits"
        assert (box / "corpus" / "a.txt").read_text(encoding="utf-8") == "before"
        assert not (box / "corpus" / "b.txt").exists()

    def test_set_asides_are_numbered(self, tmp_path: Path) -> None:
        d = tmp_path / "XC001"
        d.mkdir()
        for step in ("write-1", "audit"):
            self._session_files(d, step)
            xr.abandon(d, step, "interrupted", tmp_path / "box", None)
        assert (d / "cut" / "02-audit.jsonl").exists()


class TestSummary:
    @staticmethod
    def _pair(out: Path, pid: str, kind: str, outcome: str | None, steps: list[str]) -> None:
        d = out / pid
        d.mkdir(parents=True)
        (d / "pair.json").write_text(json.dumps({"kind": kind, "round": 1}), encoding="utf-8")
        if outcome:
            (d / "outcome.json").write_text(json.dumps({"outcome": outcome}), encoding="utf-8")
        for step in steps:
            category = "write" if step.startswith("write-") else step
            record = {"category": category, "turns": 2,
                      "usage": dict.fromkeys(xr.USAGE_KEYS, 10)}
            (d / f"{step}.json").write_text(json.dumps(record), encoding="utf-8")
        (d / "gate-1.json").write_text(json.dumps({"pass": False}), encoding="utf-8")

    def test_it_counts_by_category_including_failed_attempts(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        self._pair(out, "XC001", "bounded_input", "accepted", ["write-1", "audit"])
        self._pair(out, "XC002", "caller_held_lock", "failed", ["write-1", "write-2", "write-3"])
        self._pair(out, "XC003", "caller_held_lock", None, ["write-1"])
        cut = json.dumps({"event": "credit_cut"}) + "\n"
        (out / "events.jsonl").write_text(cut, encoding="utf-8")
        s = xr.summarize(out)
        assert (s["kinds_filled"], s["kinds"], s["windows_used"]) == (1, ["bounded_input"], 2)
        assert s["totals"]["write"]["sessions"] == 5
        assert s["totals"]["write"]["input_tokens"] == 50
        assert s["totals"]["audit"]["sessions"] == 1
        assert [r["attempts"] for r in s["pairs"]] == [1, 3, 1]
        assert s["pairs"][2]["outcome"] == "진행 중"
