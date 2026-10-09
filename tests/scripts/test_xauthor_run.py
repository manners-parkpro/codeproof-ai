"""codex 저자 실행기 (DESIGN §7.10d) - codex 를 부르지 않는 판정 · 상태 · 프롬프트만 본다.

🔴 판정이 공허하면 크레딧으로 끊긴 세션이 시도로 세어지거나, 재현되지 않은 지적이 쌍을 버리게 한다 -
   판정마다 우는 입력을 같이 둔다.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
REFUSAL_MESSAGE = (
    "This content was flagged for possible cybersecurity risk. If this seems wrong, try "
    "rephrasing your request."
)
"""안전 필터가 세션을 거절할 때의 문장 [실측 · XC010 audit · 2026-10-07 · 뒤의 안내는 줄였다]."""


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

    def test_a_safety_refusal_is_seen_and_is_not_a_credit_cut(self, tmp_path: Path) -> None:
        """🔴 거절은 세는 세션이다 - 크레딧 끊김으로 읽으면 같은 요청을 되풀이한다."""
        ev = _jsonl(
            tmp_path / "s.jsonl",
            {"type": "thread.started"},
            {"type": "error", "message": REFUSAL_MESSAGE},
            {"type": "turn.failed", "error": {"message": REFUSAL_MESSAGE}},
        )
        s = xr.read_session(ev, tmp_path / "none.err", 1, timed_out=False)
        assert (s.cut, s.refused) == (False, REFUSAL_MESSAGE)

    def test_an_ordinary_failure_is_not_a_credit_cut(self, tmp_path: Path) -> None:
        """대조 - 다른 실패까지 세지 않으면 시간 상한 · 오류로 끊긴 시도가 공짜 재시도가 된다."""
        failed: dict[str, object] = {"type": "turn.failed", "error": {"message": "stream error"}}
        ev = _jsonl(tmp_path / "s.jsonl", failed)
        s = xr.read_session(ev, tmp_path / "none.err", 1, timed_out=True)
        assert (s.cut, s.timed_out, s.refused) == (False, True, None)


class TestKindDone:
    """분류 하나를 끝내는 규칙 - 받아들인 쌍 하나 · 거절된 쌍 하나 · 실패한 쌍 넷."""

    @pytest.mark.parametrize(
        ("outcomes", "done"),
        [
            (["accepted"], True),
            (["failed"] * 4, True),
            (["refused"], True),  # 🔴 새 쌍의 첫 쓰기는 쌍 번호만 다른 같은 요청이다
            (["failed", "refused"], True),
            (["failed"] * 3, False),
            (["failed", None], False),
            ([None], False),
        ],
    )
    def test_kind_done(self, outcomes: list[str | None], done: bool) -> None:
        assert xr.kind_done(outcomes) is done


class TestStage2Inputs:
    """2단계가 이어받는 것 - 분류 · 앞서 받아들인 쌍의 요약 (선언 「쓰는 입력」 · ⑩ (e))."""

    @staticmethod
    def _pair(
        out: Path, pid: str, kind: str, outcome: str, lure: str = "미끼", *, claim: str = "주장",
    ) -> Path:
        d = out / pid
        meta = d / "final" / f"{pid}-x" / "meta.toml"
        meta.parent.mkdir(parents=True)
        meta.write_text(
            f'trap_kind = "{kind}"\n[bait]\napparent_defect = """\n{lure}\n  둘째 줄\n"""\n'
            f'[safety]\nclaim = "{claim}"\nguard_symbol = "guard"\n',
            encoding="utf-8",
        )
        (d / "pair.json").write_text(json.dumps({"kind": kind}), encoding="utf-8")
        (d / "outcome.json").write_text(json.dumps({"outcome": outcome}), encoding="utf-8")
        return d

    def test_a_brief_is_the_authors_lure_and_guard_on_one_line(self, tmp_path: Path) -> None:
        d = self._pair(tmp_path, "XC001", "bounded_input", "accepted", lure="큰 할당")
        assert xr.brief_of(d) == "미끼: 큰 할당 둘째 줄 · 가드: `guard` — 주장"

    def test_only_accepted_pairs_of_the_kind_are_given(self, tmp_path: Path) -> None:
        dirs = [
            self._pair(tmp_path, "XC003", "bounded_input", "accepted", lure="셋"),
            self._pair(tmp_path, "XC001", "bounded_input", "accepted", lure="하나"),
            self._pair(tmp_path, "XC002", "bounded_input", "failed", lure="버림"),
            self._pair(tmp_path, "XC004", "defensive_copy", "accepted", lure="다른 분류"),
        ]
        briefs = xr.accepted_briefs("bounded_input", dirs)
        assert [b.split(" · ")[0] for b in briefs] == ["미끼: 하나 둘째 줄", "미끼: 셋 둘째 줄"]

    def test_a_long_claim_is_carried_whole(self, tmp_path: Path) -> None:
        """🔴 고치거나 자르지 않는다 - 1단계 claim 은 101~253자였다 [실측]. 짧으면 못 본다."""
        claim = "가드는 " + "입력 크기를 먼저 검사하고 넘으면 할당 전에 거절한다 " * 8
        d = self._pair(tmp_path, "XC001", "bounded_input", "accepted", claim=claim)
        assert len(claim) > 200
        assert xr.brief_of(d).endswith(" — " + " ".join(claim.split()))

    def test_the_kinds_carried_on_skip_refused_and_unfilled_ones(self, tmp_path: Path) -> None:
        self._pair(tmp_path, "XC001", "bounded_input", "accepted")
        self._pair(tmp_path, "XC002", "misleading_name", "refused")
        self._pair(tmp_path, "XC003", "defensive_copy", "failed")
        assert xr.stage2_kinds(tmp_path) == ["bounded_input"]

    def test_a_refusal_closes_a_kind_that_also_has_an_accepted_pair(self, tmp_path: Path) -> None:
        """🔴 받아들인 쌍이 있어도 거절이 있으면 닫힌다 - 위 시험은 「채우지 못함」으로도 빠진다."""
        self._pair(tmp_path, "XC001", "bounded_input", "accepted")
        self._pair(tmp_path, "XC002", "defensive_copy", "accepted")
        self._pair(tmp_path, "XC003", "defensive_copy", "refused")
        assert xr.stage2_kinds(tmp_path) == ["bounded_input"]

    def test_the_declared_stage2_numbers_are_pinned(self) -> None:
        """선언 「2단계」 · 시작 전 보정 ⑥ - 일곱 바퀴 · 8분류 미만은 미완 · 창 스무 개에서 멈춘다.

        하한은 10 에서 8 로 낮췄다 (수집 중 보정 2026-10-09). 1단계 상수는 흐름 시험이 고정한다.
        2단계 시험은 이 값들을 바꿔 끼워 써서 고정하지 못한다.
        """
        assert (xr.ROUNDS, xr.MIN_KINDS, xr.STAGE2_MAX_WINDOWS) == (7, 8, 20)

    def test_a_lowered_cap_is_recorded_once_on_resume(self) -> None:
        """🔴 이어 받은 RUN.json 이 쓰지 않는 상한을 적지 않게 - 보정을 남기고 한 번만 센다."""
        rec: dict[str, Any] = {"caps": {"min_kinds": 10, "rounds": 7}}
        xr.amend(rec)
        xr.amend(rec)
        assert rec["caps"] == {"min_kinds": xr.MIN_KINDS, "rounds": 7}
        got = [(a["cap"], a["from"], a["to"]) for a in rec["amendments"]]
        assert got == [("min_kinds", 10, xr.MIN_KINDS)]

    def test_a_record_without_the_cap_is_left_alone(self) -> None:
        """1단계 RUN.json 에는 그 상한이 없다 - 보정을 지어내지 않는다."""
        rec: dict[str, Any] = {"caps": {"attempts": 3}}
        xr.amend(rec)
        assert rec == {"caps": {"attempts": 3}}

    @pytest.mark.parametrize("attempt", [1, 2])
    def test_every_attempt_carries_the_briefs(self, attempt: int) -> None:
        """시도마다 새 세션이다 - 재시도 과제에도 앞 쌍 요약이 있어야 한다."""
        task = xr.task_write("XC015", "bounded_input", attempt, "관문 실패", ("미끼: a",))
        assert "다른 기전으로 쓴다" in task
        assert "- 미끼: a\n" in task

    def test_no_briefs_no_block(self) -> None:
        assert "다른 기전" not in xr.task_write("XC001", "bounded_input", 1, None)


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


class TestGateOutput:
    """관문 출력이 끝까지 찍혔는가 - 종료 코드만으로는 쌍의 코드가 끝낸 관문을 못 가린다."""

    FULL = "XC001-x\n" + "".join(f"  ✓  {c}\n" for c in xr.GATE_CHECKS) + "\n관문 1쌍 · 통과 1\n"

    def test_a_full_pass_is_read(self) -> None:
        assert xr.gate_output_ok(self.FULL)
        assert xr.gate_output_ok(self.FULL.replace("✓  proof", "✓  proof  공격 2번"))

    @pytest.mark.parametrize("line", ["  ✓  proof\n", "\n관문 1쌍 · 통과 1\n"])
    def test_a_missing_line_is_not_a_pass(self, line: str) -> None:
        assert not xr.gate_output_ok(self.FULL.replace(line, "\n", 1))

    def test_a_failed_check_is_not_a_pass(self) -> None:
        assert not xr.gate_output_ok(self.FULL.replace("✓  mutants", "✗  mutants"))
        assert not xr.gate_output_ok("")


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

    def test_a_window_without_a_finished_session_has_not_started(self, tmp_path: Path) -> None:
        """🔴 충전 전의 재시도는 창을 쓰지 않는다 - 세면 늦은 충전 하나가 멈춤 규칙을 건다."""
        out = tmp_path / "out"
        (out / "XC001").mkdir(parents=True)
        (out / "XC001" / "write-1.json").write_text(json.dumps({"window": 1}), encoding="utf-8")
        assert xr.window_has_sessions(out)
        self._cuts(out, 1)
        assert not xr.window_has_sessions(out)
        with (out / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "credit_cut_idle"}) + "\n")
        assert xr.windows_used(out) == 2


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

    def test_cut_sessions_are_calls_without_tokens(self, tmp_path: Path) -> None:
        """끊긴 세션은 기록 없이 cut/ 으로 간다 - 호출로는 세고 토큰은 모른다."""
        out = tmp_path / "out"
        self._pair(out, "XC001", "bounded_input", None, ["write-1"])
        cut = out / "XC001" / "cut"
        cut.mkdir()
        (cut / "01-write-1.reason").write_text("credits\n", encoding="utf-8")
        (cut / "02-audit.reason").write_text("interrupted\n", encoding="utf-8")
        s = xr.summarize(out)
        cut_sessions = [s["totals"][c]["cut_sessions"] for c in ("write", "audit")]
        assert cut_sessions == [1, 1]
        assert (s["totals"]["write"]["sessions"], s["totals"]["write"]["input_tokens"]) == (1, 10)

    def test_retries_before_the_refill_are_not_calls(self, tmp_path: Path) -> None:
        """🔴 충전 전 재시도는 모델에 닿지 않았다 - 「쌍당 호출」에 섞이면 부풀려진다.

        cut/ 의 이유는 끊김과 같은 credits 다 - 이벤트(credit_cut_idle)로 가른다.
        """
        out = tmp_path / "out"
        self._pair(out, "XC001", "bounded_input", None, [])
        cut = out / "XC001" / "cut"
        cut.mkdir()
        for n in range(1, 4):
            (cut / f"{n:02d}-write-1.reason").write_text("credits\n", encoding="utf-8")
        events = [{"event": "credit_cut", "pair": "XC001", "step": "write-1"}] + [
            {"event": "credit_cut_idle", "pair": "XC001", "step": "write-1"}
        ] * 2
        (out / "events.jsonl").write_text(
            "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
        )
        write = xr.summarize(out)["totals"]["write"]
        assert (write["cut_sessions"], write["idle_sessions"]) == (1, 2)


# ── 흐름 - 가짜 codex 로 세션 → 관문 → 감사 → 재현 → 마무리를 돈다 (유료 호출 없음) ──────────────

FAKE_CODEX = r'''#!/usr/bin/env python3
"""가짜 codex - exec 은 쌍을 복사하거나 감사 답을 쓰고, sandbox 는 명령을 그대로 돈다."""
import json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
conf_path = HERE / "fake.json"
conf = json.loads(conf_path.read_text())
args = sys.argv[1:]
if args[:1] == ["sandbox"]:
    cmd = args[args.index("--") + 1:]
    sys.exit(subprocess.run(cmd, cwd=args[args.index("-C") + 1]).returncode)
box, last, prompt = Path(args[args.index("-C") + 1]), Path(args[args.index("-o") + 1]), args[-1]
n = conf["calls"]
conf["calls"] = n + 1
if conf.get("sleep_at") == n:
    conf_path.write_text(json.dumps(conf))
    import time
    time.sleep(30)
cuts = conf.get("cut_at")
if n == cuts or (isinstance(cuts, list) and n in cuts):
    conf_path.write_text(json.dumps(conf))
    (box / "stray.txt").write_text("half-written")
    print(json.dumps({"type": "error", "message": "Your workspace is out of credits."}))
    sys.exit(1)
if conf.get("refuse_at") == n:
    conf_path.write_text(json.dumps(conf))
    said = "This content was flagged for possible cybersecurity risk."
    print(json.dumps({"type": "thread.started"}))
    print(json.dumps({"type": "error", "message": said}))
    print(json.dumps({"type": "turn.failed", "error": {"message": said}}))
    sys.exit(1)
if "--output-schema" in args:
    last.write_text(json.dumps({"findings": conf["audits"].pop(0) if conf["audits"] else []}))
elif not conf.get("no_pair"):
    pid = re.search(r"쌍 식별자: `(XC\d{3})`", prompt)[1]
    dest = box / "corpus" / f"{pid}-fake"
    if not dest.exists():
        shutil.copytree(conf["source"], dest, ignore=shutil.ignore_patterns("__pycache__"))
        meta = dest / "meta.toml"
        text = re.sub(r'decoy_id = ".*"', f'decoy_id = "{dest.name}"', meta.read_text())
        if conf.get("wrong_kind"):
            text = re.sub(r'trap_kind = ".*"', 'trap_kind = "bounded_input"', text)
        meta.write_text(text)
        if conf.get("leave_notes"):
            (box / "notes.md").write_text("저자가 상자 맨 위에 남긴 메모")
            (dest / "axes.md").write_text("축 표")
    if "감사가 재현한 문제" in prompt:
        (box / "response.md").write_text("1. 고쳤다")
        if conf.get("break_on_fix"):
            (dest / "proof.py").write_text("def attack(mod):\n    return False\n")
    last.write_text(dest.name)
conf_path.write_text(json.dumps(conf))
print(json.dumps({"type": "thread.started"}))
usage = {"input_tokens": 100, "cached_input_tokens": 40}
print(json.dumps({"type": "turn.completed", "usage": usage}))
'''
GATE_PAIR = next((SCRIPT.parents[1] / "corpus" / "decoys").glob("D115-*"))
GATE_KIND = "unreachable_branch"


class TestFlowWithAFakeCodex:
    """판정이 맞아도 흐름이 틀리면 첫 유료 세션 뒤에 드러난다 - 가짜 codex 로 먼저 돈다."""

    @pytest.fixture
    def pair(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
        fake = tmp_path / "codex"
        fake.write_text(FAKE_CODEX, encoding="utf-8")
        fake.chmod(0o755)
        monkeypatch.setattr(xr.xa, "CODEX", fake)
        monkeypatch.setattr(xr.xa, "SHARED", tmp_path / "shared")
        (tmp_path / "shared").mkdir()
        out = tmp_path / "out"
        (out / "XC001").mkdir(parents=True)
        (out / "XC001" / "pair.json").write_text(json.dumps({"kind": GATE_KIND}), encoding="utf-8")
        venv = Path(sys.executable).parent.parent  # 저장소의 .venv - 진짜 관문을 돈다
        return xr.Pair(out=out, kind=GATE_KIND, pid="XC001", venv=venv)

    @staticmethod
    def _configure(p: Any, **conf: object) -> None:
        body = {"calls": 0, "source": str(GATE_PAIR), "audits": [], **conf}
        (p.out.parent / "fake.json").write_text(json.dumps(body), encoding="utf-8")

    @staticmethod
    def _finding(stdout_word: str) -> dict[str, str]:
        return {**FINDING, "repro": f"print({stdout_word!r})"}

    def test_a_pair_the_audit_cannot_break_is_accepted(self, pair: Any) -> None:
        self._configure(pair, audits=[[self._finding("NOT REPRODUCED")]])
        xr.run_pair(pair)
        outcome = json.loads((pair.d / "outcome.json").read_text(encoding="utf-8"))
        assert outcome["outcome"] == "accepted"
        assert sorted(p.name for p in (pair.d / "final" / "XC001-fake").iterdir()) == sorted(
            xr.PAIR_FILES
        )
        assert not pair.box.exists() and not pair.snap.exists()
        assert not (pair.d / "fix.json").exists()
        repro = json.loads((pair.d / "audit.repro.json").read_text(encoding="utf-8"))
        assert [f["reproduced"] for f in repro] == [False]

    def test_what_the_author_left_is_kept(self, pair: Any) -> None:
        """🔴 상자 맨 위 파일과 쌍 폴더의 덤은 기록으로 남긴다 (2단계 전 보정 ②).

        아무것도 안 남겨도 통과하던 0건 단언만 있었다."""
        self._configure(pair, audits=[[self._finding("NOT REPRODUCED")]], leave_notes=True)
        xr.run_pair(pair)
        kept = pair.d / "box-files" / "notes.md"
        assert kept.read_text(encoding="utf-8").startswith("저자가")
        outcome = json.loads((pair.d / "outcome.json").read_text(encoding="utf-8"))
        assert "axes.md" in outcome["extras"]

    def test_a_reproduced_problem_goes_through_fix_and_recheck(self, pair: Any) -> None:
        self._configure(pair, audits=[[self._finding("REPRODUCED")], []])
        xr.run_pair(pair)
        assert json.loads((pair.d / "outcome.json").read_text(encoding="utf-8"))["outcome"] == (
            "accepted"
        )
        assert "감사가 재현한 문제" in (pair.d / "fix.prompt.txt").read_text(encoding="utf-8")
        assert (pair.d / "recheck.json").exists()
        assert (pair.d / "response.md").exists()

    def test_a_credit_cut_is_not_counted_and_the_run_resumes(self, pair: Any) -> None:
        self._configure(pair, cut_at=0, audits=[[]])
        with pytest.raises(xr.Stop) as stop:
            xr.run_pair(pair)
        assert stop.value.rc == xr.CUT
        reason = (pair.d / "cut" / "01-write-1.reason").read_text(encoding="utf-8")
        assert reason.strip() == "credits"
        assert not (pair.box / "stray.txt").exists()
        assert not list((pair.box / "corpus").glob("XC001-*"))
        xr.run_pair(pair)
        s = xr.summarize(pair.out)
        assert s["pairs"][0]["outcome"] == "accepted"
        assert s["pairs"][0]["attempts"] == 1
        assert s["pairs"][0]["not_counted"] == ["credits"]
        # 첫 호출부터 끊겼다 - 이 실행은 그 창을 쓰지 않았다
        assert (s["windows_used"], s["credit_cuts"], s["idle_cuts"]) == (1, 0, 1)

    def test_retries_before_the_refill_do_not_use_windows(self, pair: Any) -> None:
        """감사에서 끊긴 뒤 (창 1 끝) 충전 전 재시도 둘이 또 끊긴다 - 창은 둘째에 머문다."""
        self._configure(pair, cut_at=[1, 2, 3], audits=[[]])  # 0 = write-1, 1~3 = audit
        for _ in range(3):
            with pytest.raises(xr.Stop) as stop:
                xr.run_pair(pair)
            assert stop.value.rc == xr.CUT
        xr.run_pair(pair)
        s = xr.summarize(pair.out)
        assert s["pairs"][0]["outcome"] == "accepted"
        assert (s["windows_used"], s["credit_cuts"], s["idle_cuts"]) == (2, 1, 2)
        audit = json.loads((pair.d / "audit.json").read_text(encoding="utf-8"))
        assert audit["window"] == 2

    def _calls(self, p: Any) -> int:
        return int(json.loads((p.out.parent / "fake.json").read_text(encoding="utf-8"))["calls"])

    def _refused_events(self, p: Any) -> list[tuple[str, str]]:
        return [(e["pair"], e["step"]) for e in xr.events_of(p.out) if e["event"] == "refused"]

    def test_a_refused_audit_ends_the_pair(self, pair: Any) -> None:
        """🔴 거절은 1급 기록 - 세션 기록 · 이벤트 하나 · 「refused」로 끝난다."""
        self._configure(pair, refuse_at=1)  # 0 = write-1, 1 = audit
        xr.run_pair(pair)
        outcome = json.loads((pair.d / "outcome.json").read_text(encoding="utf-8"))
        assert (outcome["outcome"], xr.outcome_of(pair.d)) == ("refused", "refused")
        assert "안전 필터가 거절했다" in outcome["why"]
        record = json.loads((pair.d / "audit.json").read_text(encoding="utf-8"))
        assert record["refused"] == "This content was flagged for possible cybersecurity risk."
        assert self._refused_events(pair) == [("XC001", "audit")]
        assert xr.summarize(pair.out)["refused"] == 1
        assert self._calls(pair) == 2
        assert not pair.box.exists()

    def test_what_the_old_runner_left_is_refused_on_resume(
        self, pair: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """XC010 - 거절을 모르던 실행기는 감사 결과를 못 읽어 rc 4 로 멈췄다 (refused 칸 없음).

        🔴 이어 돌면 남은 이벤트로 거절을 읽고 끝낸다 - 감사를 다시 보내지 않는다.
        """
        self._configure(pair, refuse_at=1)
        real = xr.read_session
        with monkeypatch.context() as m:
            m.setattr(xr, "read_session", lambda *a, **k: replace(real(*a, **k), refused=None))
            with pytest.raises(xr.Stop) as stop:
                xr.run_pair(pair)
        assert stop.value.rc == xr.HUMAN
        assert "스키마 모양으로 읽지 못했다" in str(stop.value)
        record = json.loads((pair.d / "audit.json").read_text(encoding="utf-8"))
        del record["refused"]
        (pair.d / "audit.json").write_text(json.dumps(record), encoding="utf-8")
        sent = self._calls(pair)
        xr.run_pair(pair)
        assert xr.outcome_of(pair.d) == "refused"
        assert self._calls(pair) == sent == 2
        assert self._refused_events(pair) == [("XC001", "audit")]

    @staticmethod
    def _source(p: Any, tail: str) -> str:
        """관문 시험 쌍의 사본 - proof.py 끝에 코드를 더한다."""
        src = p.out.parent / "source"
        shutil.copytree(GATE_PAIR, src, ignore=shutil.ignore_patterns("__pycache__"))
        proof = src / "proof.py"
        proof.write_text(proof.read_text(encoding="utf-8") + tail, encoding="utf-8")
        return str(src)

    def _outcome(self, p: Any) -> tuple[str, str]:
        o = json.loads((p.d / "outcome.json").read_text(encoding="utf-8"))
        return o["outcome"], o["why"]

    def test_a_pair_failing_the_gate_three_times_fails(self, pair: Any) -> None:
        """관문 rc 1 은 시도 실패다 - 세 번이면 쌍을 버린다. 관문이 본 판은 시도마다 남는다."""
        self._configure(pair, source=self._source(pair, "\n\ndef attack(mod):\n    return False\n"))
        xr.run_pair(pair)
        assert self._outcome(pair) == ("failed", f"관문 {xr.ATTEMPTS}번 실패")
        gates = [json.loads((pair.d / f"gate-{a}.json").read_text(encoding="utf-8"))
                 for a in range(1, xr.ATTEMPTS + 1)]
        assert [(g["pass"], g["rc"] not in (0, None)) for g in gates] == [(False, True)] * 3
        assert (pair.d / "gate-1.pair" / "proof.py").exists()

    def test_a_pair_that_ends_the_gate_early_does_not_pass(self, pair: Any) -> None:
        """🔴 쌍의 코드가 SystemExit(0) 으로 관문을 끝내면 rc 0 이어도 통과가 아니다."""
        self._configure(pair, source=self._source(pair, "\n\nraise SystemExit(0)\n"))
        xr.run_pair(pair)
        gate = json.loads((pair.d / "gate-1.json").read_text(encoding="utf-8"))
        assert (gate["pass"], gate["rc"]) == (False, 0)
        assert "검사 출력이 끝까지 없다" in (pair.d / "gate-1.txt").read_text(encoding="utf-8")
        assert xr.outcome_of(pair.d) == "failed"

    def test_a_session_at_the_time_limit_counts_as_an_attempt(
        self, pair: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """시간 상한은 크레딧 끊김이 아니다 - 시도로 센다 (공짜 재시도가 아니다)."""
        monkeypatch.setattr(xr.xa, "EXEC_TIMEOUT_S", 2)
        self._configure(pair, sleep_at=0, audits=[[]])
        xr.run_pair(pair)
        first = json.loads((pair.d / "write-1.json").read_text(encoding="utf-8"))
        assert first["timed_out"] is True
        s = xr.summarize(pair.out)
        assert (s["pairs"][0]["outcome"], s["pairs"][0]["attempts"]) == ("accepted", 2)
        assert (s["credit_cuts"], s["idle_cuts"], s["pairs"][0]["not_counted"]) == (0, 0, [])

    def test_an_interrupted_session_is_set_aside_and_run_again(self, pair: Any) -> None:
        """하네스가 중단한 세션(이벤트만 남음)은 세지 않고 그 전 상자로 되돌려 다시 돈다."""
        self._configure(pair, audits=[[]])
        xr.make_box(pair.box)
        xr.snapshot(pair.box, pair.snap)
        (pair.box / "stray.txt").write_text("반쯤 쓴 것", encoding="utf-8")
        (pair.d / "write-1.jsonl").write_text('{"type": "thread.started"}\n', encoding="utf-8")
        xr.run_pair(pair)
        reason = (pair.d / "cut" / "01-write-1.reason").read_text(encoding="utf-8")
        assert reason.strip() == "interrupted"
        assert not (pair.d / "box-files" / "stray.txt").exists()
        s = xr.summarize(pair.out)
        assert (s["pairs"][0]["outcome"], s["pairs"][0]["attempts"]) == ("accepted", 1)
        assert (s["interrupted"], s["windows_used"]) == (1, 1)
        assert s["totals"]["write"]["cut_sessions"] == 1

    def test_a_problem_left_at_the_recheck_fails_the_pair(self, pair: Any) -> None:
        found = [self._finding("REPRODUCED")]
        self._configure(pair, audits=[found, found])
        xr.run_pair(pair)
        assert self._outcome(pair) == ("failed", "재확인에서 재현되는 문제가 남았다")

    def test_a_fix_that_breaks_the_gate_fails_the_pair(self, pair: Any) -> None:
        self._configure(pair, audits=[[self._finding("REPRODUCED")]], break_on_fix=True)
        xr.run_pair(pair)
        assert self._outcome(pair) == ("failed", "고친 뒤 관문을 넘지 못했다")
        assert not (pair.d / "recheck.json").exists()

    def test_a_missing_box_after_a_write_stops_for_a_human(self, pair: Any) -> None:
        self._configure(pair)
        (pair.d / "write-1.json").write_text("{}", encoding="utf-8")
        with pytest.raises(xr.Stop) as stop:
            xr.run_pair(pair)
        assert stop.value.rc == xr.HUMAN

    def test_a_kind_ends_after_four_failed_pairs(
        self, pair: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """분류마다 실패한 쌍은 넷까지 - run 전체를 돈다 (관문을 돌 쌍이 없어 빠르다)."""
        monkeypatch.setattr(xr, "preflight", lambda _out: pair.venv)
        monkeypatch.setattr(xr, "KINDS", [GATE_KIND])
        self._configure(pair, no_pair=True)
        assert xr.run(pair.out) == xr.DONE
        outcomes = [xr.outcome_of(d) for d in xr.pair_dirs(pair.out)]
        assert outcomes == ["failed"] * xr.FAILED_PER_KIND
        summary = json.loads((pair.out / "summary.json").read_text(encoding="utf-8"))
        assert summary["kinds_filled"] == 0

    # ── 2단계 - 1단계를 이어 바퀴 2~8 ─────────────────────────────────────────

    @staticmethod
    def _stage1(root: Path, *outcomes: str) -> Path:
        """1단계 출력 - 관문 시험 쌍을 받아들인 쌍으로 둔다 (final/ 의 메타가 요약의 출처)."""
        after = root / "stage1"
        for n, outcome in enumerate(outcomes, 1):
            d = after / f"XC{n:03d}"
            (d / "final").mkdir(parents=True)
            shutil.copytree(GATE_PAIR, d / "final" / f"XC{n:03d}-fake",
                            ignore=shutil.ignore_patterns("__pycache__"))
            (d / "pair.json").write_text(json.dumps({"kind": GATE_KIND}), encoding="utf-8")
            (d / "outcome.json").write_text(json.dumps({"outcome": outcome}), encoding="utf-8")
        (after / "RUN.json").write_text(json.dumps(xr.signed_fields()), encoding="utf-8")
        return after

    @staticmethod
    def _stage2(p: Any, monkeypatch: pytest.MonkeyPatch, *, rounds: int = 2) -> Path:
        out: Path = p.out.parent / "stage2"
        venv: Path = p.venv

        def fake_preflight(o: Path, stage2: dict[str, object] | None = None) -> Path:
            o.mkdir(parents=True, exist_ok=True)
            # 진짜 preflight 처럼 2단계 정보(after · kinds)를 싣는다
            if not (o / "RUN.json").exists():
                rec = {"rounds": {}, **(stage2 or {})}
                (o / "RUN.json").write_text(json.dumps(rec), encoding="utf-8")
            return venv

        monkeypatch.setattr(xr, "preflight", fake_preflight)
        monkeypatch.setattr(xr, "check_catalog", lambda: "note")
        monkeypatch.setattr(xr, "KINDS", [GATE_KIND])
        monkeypatch.setattr(xr, "ROUNDS", rounds)
        monkeypatch.setattr(xr, "MIN_KINDS", 1)
        return out

    def test_stage2_writes_each_round_with_the_accepted_pairs_so_far(
        self, pair: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """바퀴마다 분류마다 한 쌍 · 앞서 받아들인 쌍의 요약이 쌓인다 · 쌍 번호는 1단계에 잇는다."""
        after = self._stage1(pair.out.parent, "accepted")
        out = self._stage2(pair, monkeypatch)
        self._configure(pair, audits=[[], []])
        assert xr.run_stage2(out, after) == xr.DONE
        assert [(d.name, xr.pair_round(d), xr.outcome_of(d)) for d in xr.pair_dirs(out)] == [
            ("XC002", 2, "accepted"), ("XC003", 3, "accepted"),
        ]
        briefs = [
            [ln for ln in (out / pid / "write-1.prompt.txt").read_text(encoding="utf-8").split("\n")
             if ln.startswith("- 미끼: ")]
            for pid in ("XC002", "XC003")
        ]
        assert [len(b) for b in briefs] == [1, 2]
        run = json.loads((out / "RUN.json").read_text(encoding="utf-8"))
        assert sorted(run["rounds"]) == ["2", "3"]

    def test_a_kind_that_misses_a_round_is_dropped_and_the_stage_is_incomplete(
        self, pair: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """🔴 바퀴 하나를 못 채운 분류는 8쌍이 못 된다 - 이후 바퀴는 안 쓴다 (하한 미만은 미완)."""
        after = self._stage1(pair.out.parent, "accepted")
        out = self._stage2(pair, monkeypatch)
        self._configure(pair, no_pair=True)
        assert xr.run_stage2(out, after) == xr.STOP
        rows = [(xr.pair_round(d), xr.outcome_of(d)) for d in xr.pair_dirs(out)]
        assert rows == [(2, "failed")] * xr.FAILED_PER_KIND
        assert "미완" in xr.events_of(out)[-1]["why"]
        summary = xr.summarize(out)
        assert summary["complete_kinds"] == [] and summary["dropped"] == {GATE_KIND: 2}, (
            "통째로 뺀 분류를 「채운 분류」로 읽지 않게 따로 적는다 (F5a)"
        )

    def test_stage2_stops_past_its_window_budget(
        self, pair: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        after = self._stage1(pair.out.parent, "accepted")
        out = self._stage2(pair, monkeypatch)
        out.mkdir()
        cut = json.dumps({"event": "credit_cut"}) + "\n"
        (out / "events.jsonl").write_text(cut * xr.STAGE2_MAX_WINDOWS, encoding="utf-8")
        self._configure(pair)
        assert xr.run_stage2(out, after) == xr.STOP
        assert xr.pair_dirs(out) == []

    def test_stage2_refuses_settings_that_differ_from_stage1(
        self, pair: Any, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        after = self._stage1(pair.out.parent, "accepted")
        record = json.loads((after / "RUN.json").read_text(encoding="utf-8"))
        (after / "RUN.json").write_text(json.dumps({**record, "effort": "low"}), encoding="utf-8")
        out = self._stage2(pair, monkeypatch)
        self._configure(pair)
        assert xr.run_stage2(out, after) == xr.HUMAN

    def test_a_wrong_kind_fails_the_gate_three_times(self, pair: Any) -> None:
        self._configure(pair, wrong_kind=True)
        xr.run_pair(pair)
        outcome = json.loads((pair.d / "outcome.json").read_text(encoding="utf-8"))
        assert outcome["outcome"] == "failed"
        assert [(pair.d / f"gate-{a}.json").exists() for a in (1, 2, 3)] == [True] * 3
        retry = (pair.d / "write-2.prompt.txt").read_text(encoding="utf-8")
        assert "trap_kind 는 unreachable_branch 여야 한다" in retry
