"""측정 뒤 claude 감사 실행기 (DESIGN §7.10d) - claude 를 부르지 않는 판정 · 상태 · 프롬프트만 본다.

🔴 판정이 공허하면 다른 모델의 답이 감사로 실리거나, 위협 모델 밖 판정이 라벨 문제로 세어지거나,
   측정 전에 쌍을 본다 - 판정마다 우는 입력을 같이 둔다.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "claude_audit.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("claude_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ca = _load()
MODEL = "claude-test-1"
FINDING = {"kind": "false_claim", "lines": "3-5", "summary": "s", "evidence": "e", "repro": "r"}


def _envelope(**over: object) -> dict[str, object]:
    return {
        "type": "result", "subtype": "success", "is_error": False, "stop_reason": "tool_use",
        "modelUsage": {MODEL: {"outputTokens": 3}}, "structured_output": {"findings": []},
        **over,
    }


class TestAnswer:
    def test_the_structured_answer_is_read(self) -> None:
        env = _envelope(structured_output={"findings": [FINDING]})
        assert ca.answer(env, MODEL, "findings") == {"findings": [FINDING]}

    def test_an_error_is_unreadable(self) -> None:
        with pytest.raises(ValueError, match="is_error"):
            ca.answer(_envelope(is_error=True, result="limit"), MODEL, "findings")

    def test_another_model_is_refused(self) -> None:
        """🔴 다른 모델이 답했으면 감사한 것이 claude 측정의 모델이 아니다 (D5 의 fallbacks)."""
        env = _envelope(modelUsage={"claude-other-2": {"outputTokens": 3}})
        with pytest.raises(ValueError, match="고정한 모델"):
            ca.answer(env, MODEL, "findings")

    def test_an_answer_only_in_the_text_is_unreadable(self) -> None:
        env = _envelope(structured_output=None, result='{"findings": []}')
        with pytest.raises(ValueError, match="스키마"):
            ca.answer(env, MODEL, "findings")


class TestVerdicts:
    @staticmethod
    def _last(tmp_path: Path, *findings: object, verdict: str = "IN") -> Path:
        path = tmp_path / "last.json"
        items = [{"finding": n, "verdict": verdict, "basis": "b"} for n in findings]
        path.write_text(json.dumps({"verdicts": items}), encoding="utf-8")
        return path

    def test_each_finding_once_is_read_in_order(self, tmp_path: Path) -> None:
        got = ca.verdicts_of(self._last(tmp_path, 2, 1), 2)
        assert [v["finding"] for v in got] == [1, 2]

    @pytest.mark.parametrize("findings", [(1,), (1, 1), (1, 3), (1, 2, 3), (True, 2)])
    def test_a_missing_or_extra_finding_is_unreadable(
        self, tmp_path: Path, findings: tuple[object, ...]
    ) -> None:
        """🔴 판정이 빠진 지적은 「IN 아님」으로 읽힌다 - 라벨 문제가 조용히 사라진다."""
        assert ca.verdicts_of(self._last(tmp_path, *findings), 2) is None

    def test_an_unknown_verdict_is_unreadable(self, tmp_path: Path) -> None:
        assert ca.verdicts_of(self._last(tmp_path, 1, verdict="MAYBE"), 1) is None


class TestFixedDocuments:
    def test_the_judge_head_is_the_committed_one(self) -> None:
        """🔴 측정 전에 커밋하고 바꾸지 않는다 - 바꾸면 상수도 바뀐다."""
        assert hashlib.sha256(ca.JUDGE_HEAD.read_bytes()).hexdigest() == ca.JUDGE_HEAD_SHA256

    def test_the_judge_head_carries_the_audit_threat_model_verbatim(self) -> None:
        """🔴 손으로 줄인 위협 모델은 덮는 범위 안의 결함을 거른다 (G3a1) - 감사와 같은 문면."""
        audit = ca.xr.AUDIT_HEAD.read_text(encoding="utf-8")
        block = audit[audit.index("- 안:") :].split("\n\n", 1)[0]
        assert "- 밖:" in block
        assert block in ca.JUDGE_HEAD.read_text(encoding="utf-8")

    def test_the_schema_vocabulary_is_the_runner_vocabulary(self) -> None:
        schema = json.loads(ca.JUDGE_SCHEMA.read_text(encoding="utf-8"))
        item = schema["properties"]["verdicts"]["items"]["properties"]
        assert tuple(item["verdict"]["enum"]) == ca.VERDICTS


PAIR = next((REPO / "corpus" / "decoys").glob("D115-*"))
PROBLEM = {
    **FINDING, "repro": "print('REPRODUCED')", "reproduced": True, "rc": 0, "timed_out": False,
    "stdout_tail": "trying\nREPRODUCED", "stderr_tail": "",
}


class TestJudgePrompt:
    def test_it_carries_each_problem_and_its_output(self) -> None:
        second = {**PROBLEM, "repro": "print(2)", "stderr_tail": "Traceback: boom"}
        prompt = ca.judge_prompt(PAIR, [PROBLEM, second])
        assert "=== 지적 1 — false_claim · decoy.py 3-5 ===" in prompt
        assert "=== 지적 2" in prompt
        assert "print('REPRODUCED')" in prompt and "print(2)" in prompt
        assert "trying\nREPRODUCED" in prompt and "Traceback: boom" in prompt

    def test_the_pair_is_rendered_like_the_audit(self) -> None:
        head = ca.JUDGE_HEAD.read_text(encoding="utf-8").rstrip()
        assert ca.judge_prompt(PAIR, [PROBLEM]).startswith(ca.audit_prompt(PAIR, head) + "\n\n")


class TestMeasuredFirst:
    def test_a_finished_measurement_names_the_claude_model(self) -> None:
        """목표 150쌍의 두 묶음은 코퍼스 전부를 쟀다 - 같은 재생으로 「끝났다」를 잰다."""
        got = ca.measured_model(REPO / "corpus" / "decoys", REPO / "results" / "agent")
        assert got == ca.accepted_model()

    def test_without_both_bundles_it_is_not_measured(self, tmp_path: Path) -> None:
        assert ca.measured_model(REPO / "corpus" / "decoys", tmp_path) is None


# ── 흐름 - 가짜 claude 로 감사 → 재현 → 판정 → 목록을 돈다 (구독 사용 없음) ──────────────

FAKE_CLAUDE = r'''
"""가짜 claude - 스키마로 감사 · 판정을 가르고 줄 세운 답을 낸다. 본 것을 seen.jsonl 에 남긴다."""
import json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
conf_path = HERE / "fake.json"
conf = json.loads(conf_path.read_text())
args = sys.argv[1:]
if args == ["--version"]:
    print(conf["version"])
    sys.exit(0)
n = conf["calls"]
conf["calls"] = n + 1
step = "judge" if '"verdicts"' in args[args.index("--json-schema") + 1] else "audit"
with (HERE / "seen.jsonl").open("a") as f:
    f.write(json.dumps({
        "step": step, "env": sorted(os.environ), "cwd": os.getcwd(), "left": os.listdir("."),
        "flags": [a for a in args if a.startswith("--")], "tools": args[args.index("--tools") + 1],
    }) + "\n")
model = args[args.index("--model") + 1]
env = {
    "type": "result", "subtype": "success", "is_error": False, "num_turns": 2,
    "stop_reason": "tool_use", "permission_denials": [],
    "usage": {"input_tokens": 10, "cache_read_input_tokens": 5, "output_tokens": 3},
    "modelUsage": {model: {"outputTokens": 3}},
}
if conf.get("error_at") == n:
    env |= {"is_error": True, "subtype": "error_during_execution", "result": "boom"}
elif conf.get("refuse_at") == n:
    env |= {"stop_reason": "refusal", "result": ""}
else:
    queue = conf["judges" if step == "judge" else "audits"]
    env["structured_output"] = {
        "verdicts" if step == "judge" else "findings": queue.pop(0) if queue else []
    }
conf_path.write_text(json.dumps(conf))
print(json.dumps(env))
'''
FAKE_CODEX = r'''
import subprocess, sys
args = sys.argv[1:]
cmd = args[args.index("--") + 1:]
sys.exit(subprocess.run(cmd, cwd=args[args.index("-C") + 1]).returncode)
'''


def _script(path: Path, body: str) -> Path:
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(0o755)
    return path


class TestFlowWithAFakeClaude:
    """판정이 맞아도 흐름이 틀리면 첫 구독 호출 뒤에 드러난다 - 가짜 claude 로 먼저 돈다."""

    @pytest.fixture
    def run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
        fakes = tmp_path / "fakes"
        fakes.mkdir()
        monkeypatch.setattr(ca, "CLAUDE", _script(fakes / "claude", FAKE_CLAUDE))
        monkeypatch.setattr(ca.xa, "CODEX", _script(fakes / "codex", FAKE_CODEX))
        monkeypatch.setattr(ca.xa, "SHARED", tmp_path)
        monkeypatch.setattr(ca, "VENV", Path(sys.executable).parent.parent)
        monkeypatch.setattr(ca, "accepted_model", lambda: MODEL)
        monkeypatch.setattr(ca, "measured_model", lambda *_: MODEL)
        corpus = tmp_path / "corpus"
        shutil.copytree(PAIR, corpus / PAIR.name, ignore=shutil.ignore_patterns("__pycache__"))
        out, issues = tmp_path / "out", tmp_path / "issues"

        def go(**conf: object) -> int:
            if conf:
                body = {
                    "calls": 0, "audits": [], "judges": [], "version": ca.CLAUDE_VERSION, **conf,
                }
                (fakes / "fake.json").write_text(json.dumps(body), encoding="utf-8")
            return int(ca.run(out, corpus=corpus, agents=tmp_path, issues=issues))

        return SimpleNamespace(go=go, out=out, issues=issues, fakes=fakes)

    @staticmethod
    def _calls(run: Any) -> int:
        return int(json.loads((run.fakes / "fake.json").read_text(encoding="utf-8"))["calls"])

    @staticmethod
    def _listed(run: Any, judge: str) -> list[str]:
        text = (run.issues / f"claude-audit-{judge}.txt").read_text(encoding="utf-8")
        return [ln for ln in text.split("\n") if ln and not ln.startswith("#")]

    @staticmethod
    def _found(word: str) -> list[dict[str, str]]:
        return [{**FINDING, "repro": f"print({word!r})"}]

    def test_only_an_in_verdict_lists_the_pair(self, run: Any) -> None:
        """🔴 판정자 B 의 OUT 을 세면 위협 모델 밖 재현이 주 지표에서 쌍을 지운다."""
        rc = run.go(audits=[self._found("REPRODUCED")], judges=[[_v("IN")], [_v("OUT")]])
        assert rc == 0
        assert (self._listed(run, "A"), self._listed(run, "B")) == ([PAIR.name], [])
        summary = json.loads((run.out / "summary.json").read_text(encoding="utf-8"))
        assert summary["agreement"] == "0/1"
        assert summary["verdicts"] == {"A": {"IN": 1}, "B": {"OUT": 1}}

    def test_a_problem_that_does_not_reproduce_is_not_judged(self, run: Any) -> None:
        assert run.go(audits=[self._found("NOT REPRODUCED")]) == 0
        assert self._calls(run) == 1
        assert (self._listed(run, "A"), self._listed(run, "B")) == ([], [])

    def test_a_finished_pair_is_not_asked_again(self, run: Any) -> None:
        assert run.go(audits=[self._found("REPRODUCED")], judges=[[_v("IN")], [_v("IN")]]) == 0
        assert run.go() == 0
        assert self._calls(run) == 3

    def test_an_unreadable_answer_is_set_aside_and_asked_again(self, run: Any) -> None:
        assert run.go(error_at=0) == ca.HUMAN
        cut = run.out / PAIR.name / "cut"
        assert (cut / "01-audit.reason").read_text(encoding="utf-8").startswith("is_error")
        assert not (run.out / PAIR.name / "audit.json").exists()
        assert run.go() == 0
        assert self._calls(run) == 2

    def test_a_refusal_is_kept_and_not_asked_again(self, run: Any) -> None:
        """🔴 거절은 1급 기록이다 (D5) - 다시 물어 넘기지 않는다. 목록에는 주석으로 남는다."""
        assert run.go(audits=[self._found("REPRODUCED")], judges=[[_v("IN")]], refuse_at=1) == 0
        assert json.loads((run.out / PAIR.name / "judge-A.json").read_text())["refused"]
        assert run.go() == 0
        assert self._calls(run) == 3
        text = (run.issues / "claude-audit-A.txt").read_text(encoding="utf-8")
        assert f"# 거절된 세션이 있는 쌍: {PAIR.name} judge-A" in text
        assert (self._listed(run, "A"), self._listed(run, "B")) == ([], [PAIR.name])

    def test_the_session_is_isolated(self, run: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """🔴 띄운 세션의 effort · 소켓이 새면 측정 조건이 개인 설정이 된다 (A2b)."""
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "max")
        assert run.go(audits=[self._found("NOT REPRODUCED")]) == 0
        seen = json.loads((run.fakes / "seen.jsonl").read_text(encoding="utf-8"))
        assert not {"CLAUDECODE", "CLAUDE_CODE_EFFORT_LEVEL"} & set(seen["env"])
        assert seen["left"] == [] and not seen["cwd"].startswith(str(REPO))
        assert seen["tools"] == ""
        assert {"--safe-mode", "--strict-mcp-config", "--no-session-persistence"} <= set(
            seen["flags"]
        )

    def test_the_audit_waits_for_the_measurement(
        self, run: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """🔴 claude 는 측정 전에 쌍 내용에 관여하지 않는다 (선언 「시도 · 렌즈」)."""
        monkeypatch.setattr(ca, "measured_model", lambda *_: None)
        assert run.go(audits=[self._found("REPRODUCED")]) == ca.HUMAN
        assert self._calls(run) == 0

    def test_another_cli_version_is_refused(self, run: Any) -> None:
        """🔴 자동 업데이트된 판은 측정한 제품이 아니다 - 격리 설치한 판만 부른다."""
        assert run.go(audits=[], version="2.1.286 (Claude Code)") == ca.HUMAN
        assert self._calls(run) == 0
        assert not (run.out / "RUN.json").exists()

    def test_a_different_setting_is_refused_on_resume(self, run: Any) -> None:
        assert run.go(audits=[]) == 0
        record = json.loads((run.out / "RUN.json").read_text(encoding="utf-8"))
        record["effort"] = "low"
        (run.out / "RUN.json").write_text(json.dumps(record), encoding="utf-8")
        assert run.go() == ca.HUMAN

    def test_a_different_list_is_not_overwritten(self, run: Any) -> None:
        """판정은 한 번이다 - 다시 돌린 판정이 앞 목록을 조용히 덮지 않는다."""
        run.issues.mkdir()
        (run.issues / "claude-audit-A.txt").write_text("XC999-other\n", encoding="utf-8")
        assert run.go(audits=[]) == ca.HUMAN


def _v(verdict: str) -> dict[str, object]:
    return {"finding": 1, "verdict": verdict, "basis": "b"}
