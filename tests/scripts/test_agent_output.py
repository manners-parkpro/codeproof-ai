"""review-with-agent.sh 의 판정 로직 - 에이전트 없이 깨뜨려 본다 (H3).

계약은 두 줄이다: 정상은 통과하고, 위반은 **잡힌다**. 한 줄만 보면
`return` 하나로 끝나는 무능한 가드도 통과한다.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pytest

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agent_output.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("agent_output", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ao = _load()

FINDING = {
    "file": "module.py", "line_start": 3, "line_end": 4, "category": "correctness",
    "severity": "error", "quoted_code": "x = 1", "message": "m", "failure_mode": "f",
}


def _envelope(model: str = "claude-fable-5-1", **over: object) -> dict[str, object]:
    env: dict[str, object] = {
        "is_error": False,
        "subtype": "success",
        "num_turns": 3,
        "result": json.dumps({"findings": [FINDING]}),
        "structured_output": {"findings": [FINDING]},
        "permission_denials": [],
        "modelUsage": {model: {"outputTokens": 90, "canonicalModel": model}},
    }
    env.update(over)
    return env


class TestMeasuredDigest:
    """🔴 회차마다 잰 코드의 지문을 옆 파일로 남긴다 - pack 이 지금 코드와 견준다 (DESIGN §9-5)."""

    SID = "D001-x#twin"

    def _paths(self, tmp_path: Path, digest: object) -> tuple[list[str], Path, Path]:
        manifest = tmp_path / "MANIFEST.json"
        row: dict[str, object] = {"sample_id": self.SID}
        if digest is not None:
            row["digest"] = digest
        manifest.write_text(json.dumps({"samples": [row]}), encoding="utf-8")
        prefix = str(tmp_path / f"{self.SID}.0.a0")
        Path(prefix + ".claude.json").write_text(json.dumps(_envelope()), encoding="utf-8")
        dest = tmp_path / f"{self.SID}.0.json"
        argv = ["extract", "claude", prefix, "claude-fable-5-1", str(dest), str(manifest), self.SID]
        return argv, dest, tmp_path / f"{self.SID}.0.digest"

    def test_the_digest_lands_beside_the_output(self, tmp_path: Path) -> None:
        argv, dest, side = self._paths(tmp_path, "b" * 64)
        assert ao.main(argv) == 0
        assert json.loads(dest.read_text(encoding="utf-8")) == {"findings": [FINDING]}
        assert side.read_text(encoding="utf-8") == "b" * 64 + "\n"

    @pytest.mark.parametrize("digest", [None, "b" * 63, "B" * 64], ids=["없음", "짧음", "대문자"])
    def test_without_a_digest_nothing_is_written(self, tmp_path: Path, digest: object) -> None:
        """출력만 남으면 다음 세션이 그 회차를 건너뛰고 pack 이 거부한다 - 아무것도 쓰지 않는다."""
        argv, dest, side = self._paths(tmp_path, digest)
        assert ao.main(argv) == 1
        assert not dest.exists()
        assert not side.exists()

    def test_every_box_needs_a_digest(self, tmp_path: Path) -> None:
        export = tmp_path / "export"
        for sid in ("D001", "D001#twin"):
            (export / sid).mkdir(parents=True)
        manifest = export / "MANIFEST.json"
        manifest.write_text(
            json.dumps({"samples": [{"sample_id": "D001", "digest": "c" * 64}]}), encoding="utf-8"
        )
        assert ao.main(["digests", str(manifest), str(export)]) == 1
        manifest.write_text(
            json.dumps({"samples": [
                {"sample_id": "D001", "digest": "c" * 64},
                {"sample_id": "D001#twin", "digest": "d" * 64},
            ]}),
            encoding="utf-8",
        )
        assert ao.main(["digests", str(manifest), str(export)]) == 0


class TestClaudeModelIsPinned:
    """🔴 고정한 모델이 아닌 모델이 답하면 측정 대상이 바뀐 것이다 (D5 fallbacks)."""

    def test_pinned_model_passes(self) -> None:
        payload, meta = ao.extract_claude(_envelope(), "claude-fable-5-1")
        assert payload["findings"] == [FINDING]
        assert "denials=0" in meta

    def test_substituted_model_is_refused(self) -> None:
        with pytest.raises(ao.RefusedError, match="고정한 모델이 답하지 않았다"):
            ao.extract_claude(_envelope("claude-opus-5-5"), "claude-fable-5-1")

    def test_a_second_model_beside_the_pinned_one_is_refused(self) -> None:
        """🔴 거절 대체 - 고정 모델이 거절한 턴을 다른 모델이 이어 답하면 두 모델이 다 든다."""
        env = _envelope()
        env["modelUsage"] = {
            "claude-fable-5-1": {"outputTokens": 0, "canonicalModel": "claude-fable-5-1"},
            "claude-opus-4-8": {"outputTokens": 3},
        }
        with pytest.raises(ao.RefusedError, match="고정한 모델 밖의 모델도 답했다"):
            ao.extract_claude(env, "claude-fable-5-1")

    def test_error_envelope_is_refused(self) -> None:
        with pytest.raises(ao.RefusedError, match="is_error"):
            ao.extract_claude(_envelope(is_error=True), "claude-fable-5-1")

    def test_falls_back_to_result_text(self) -> None:
        env = _envelope(structured_output=None, result="산문 " + json.dumps({"findings": []}))
        payload, _ = ao.extract_claude(env, "claude-fable-5-1")
        assert payload == {"findings": []}

    def test_unreadable_denials_are_unknown_not_a_crash(self) -> None:
        """경계 - 거부 목록이 목록이 아니면 개수를 모른다고 적는다 (감사가 따로 짚는다)."""
        _, meta = ao.extract_claude(_envelope(permission_denials=True), "claude-fable-5-1")
        assert "denials=?" in meta


class TestResolve:
    def test_claude_takes_the_model_that_did_the_work(self) -> None:
        # 보조 작업에 작은 모델이 섞여도 출력 토큰이 많은 쪽이 답한 모델이다.
        env = _envelope()
        env["modelUsage"] = {
            "claude-haiku-4-5": {"outputTokens": 5},
            "claude-fable-5-1": {"outputTokens": 90, "canonicalModel": "claude-fable-5-1"},
        }
        assert ao.resolve_claude(env) == "claude-fable-5-1"

    def test_claude_without_usage_is_refused(self) -> None:
        with pytest.raises(ao.RefusedError):
            ao.resolve_claude(_envelope(modelUsage={}))

    CATALOG: ClassVar[dict[str, object]] = {
        "models": [
            {"slug": "hidden", "priority": 1, "visibility": "hide",
             "supported_reasoning_levels": [{"effort": "low"}]},
            {"slug": "second", "priority": 3, "visibility": "list",
             "supported_reasoning_levels": [{"effort": "low"}]},
            {"slug": "top", "priority": 2, "visibility": "list",
             "supported_reasoning_levels": [{"effort": "low"}, {"effort": "high"}]},
        ]
    }

    def test_codex_top_is_the_vendors_first_listed(self) -> None:
        # 숨긴 모델은 순위가 앞서도 고르지 않는다 - 벤더가 공개한 순위다.
        assert ao.resolve_codex(self.CATALOG, "low") == "top"

    def test_codex_refuses_unsupported_effort(self) -> None:
        with pytest.raises(ao.RefusedError, match="effort"):
            ao.resolve_codex(self.CATALOG, "max")

    @pytest.mark.parametrize("model", [None, "top"])
    def test_unreadable_effort_levels_are_unsupported(self, model: str | None) -> None:
        """경계 - 카탈로그의 effort 목록을 읽지 못하면 지원하지 않는 것으로 거부한다."""
        catalog = {"models": [{"slug": "top", "priority": 1, "visibility": "list",
                               "supported_reasoning_levels": 5}]}
        with pytest.raises(ao.RefusedError, match="effort"):
            ao.resolve_codex(catalog, "low", model)

    def test_codex_pinned_model_must_exist(self) -> None:
        assert ao.resolve_codex(self.CATALOG, "low", "second") == "second"
        with pytest.raises(ao.RefusedError, match="없는 모델"):
            ao.resolve_codex(self.CATALOG, "low", "nope")

    def test_codex_description_is_read_from_the_catalog(self) -> None:
        catalog = {"models": [{"slug": "top", "description": "Frontier"}, {"slug": "second"}]}
        assert ao.describe_codex(catalog, "top") == "Frontier"
        assert ao.describe_codex(catalog, "second") == ""
        assert ao.describe_codex(catalog, "nope") == ""


class TestModelDriftStops:
    """🔴 벤더 최상위가 바뀌면 조용히 따라가지 않는다 - 순위는 벤더가, 받아들이는 것은 사람이."""

    def test_first_resolution_is_recorded(self, tmp_path: Path) -> None:
        lock = tmp_path / "agent-models.json"
        assert ao.check_model(lock, "codex", "astra", "Frontier") is None
        entry = json.loads(lock.read_text(encoding="utf-8"))["codex"]
        assert entry == {"model": "astra", "note": "Frontier"}

    def test_same_model_passes_without_rewriting(self, tmp_path: Path) -> None:
        lock = tmp_path / "agent-models.json"
        ao.check_model(lock, "codex", "astra", "Frontier")
        before = lock.stat().st_mtime_ns
        assert ao.check_model(lock, "codex", "astra", "Frontier") is None
        assert lock.stat().st_mtime_ns == before

    def test_a_different_model_stops_and_keeps_the_baseline(self, tmp_path: Path) -> None:
        # 카탈로그가 바뀌어 priority 최상위가 일상용 모델이 된 경우 [실측 2026-09-30]
        lock = tmp_path / "agent-models.json"
        ao.check_model(lock, "codex", "astra", "Frontier")
        reason = ao.check_model(lock, "codex", "sol", "Latest workhorse")
        assert reason is not None
        assert "astra" in reason and "sol" in reason and "ACCEPT_MODEL_CHANGE" in reason
        # 기준을 지키는 쪽이 그대로 복사해 쓸 수 있는 명령이어야 한다 - 받아들이는 쪽만
        # 구체적이면 멈춘 자리에서 그쪽으로 기운다.
        assert "--model astra" in reason
        assert json.loads(lock.read_text(encoding="utf-8"))["codex"]["model"] == "astra"

    def test_accepting_moves_the_baseline(self, tmp_path: Path) -> None:
        lock = tmp_path / "agent-models.json"
        ao.check_model(lock, "codex", "astra", "Frontier")
        assert ao.check_model(lock, "codex", "sol", "Latest workhorse", accept=True) is None
        assert json.loads(lock.read_text(encoding="utf-8"))["codex"]["model"] == "sol"

    def test_agents_are_tracked_separately(self, tmp_path: Path) -> None:
        lock = tmp_path / "agent-models.json"
        ao.check_model(lock, "claude", "fable", "best 별칭")
        assert ao.check_model(lock, "codex", "astra", "Frontier") is None
        assert ao.check_model(lock, "claude", "fable", "best 별칭") is None

    def test_the_cli_refuses_with_exit_4(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        lock = tmp_path / "agent-models.json"
        assert ao.main(["check-model", str(lock), "codex", "astra", "Frontier"]) == 0
        assert ao.main(["check-model", str(lock), "codex", "sol", "workhorse"]) == 4
        assert "벤더 최상위가 바뀌었다" in capsys.readouterr().out

    def test_the_committed_baseline_pins_todays_models(self) -> None:
        # 기준이 비어 있으면 CLI 를 올린 뒤의 첫 실행이 일상용 모델을 기준으로 삼는다
        # - 가드가 무력해진다.
        data = json.loads((SCRIPT.parent / "agent-models.json").read_text(encoding="utf-8"))
        assert {"claude", "codex"} <= set(data)
        assert all(entry.get("model") for entry in data.values())


class TestRunRecordRefusesMixing:
    """🔴 한 출력 디렉터리에 두 설정이 섞이면 그건 한 실행이 아니다 (F1)."""

    FIELDS: ClassVar[dict[str, str]] = dict.fromkeys(ao.CONFIG_KEYS, "v") | {"timeout_s": "240"}

    def test_same_config_resumes(self, tmp_path: Path) -> None:
        path = tmp_path / "RUN.json"
        assert ao.record(path, dict(self.FIELDS)) == []
        assert ao.record(path, dict(self.FIELDS)) == []

    def test_different_effort_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "RUN.json"
        ao.record(path, dict(self.FIELDS))
        diffs = ao.record(path, dict(self.FIELDS) | {"effort": "high"})
        assert len(diffs) == 1
        assert diffs[0].startswith("effort")

    def test_different_docstring_knob_is_refused(self, tmp_path: Path) -> None:
        """🔴 손잡이가 다르면 입력 코드가 다르다 - 이어 쓰면 keep 과 neutral 이 한 실행이 된다."""
        path = tmp_path / "RUN.json"
        ao.record(path, dict(self.FIELDS) | {"docstrings": "keep"})
        diffs = ao.record(path, dict(self.FIELDS) | {"docstrings": "neutral"})
        assert len(diffs) == 1
        assert diffs[0].startswith("docstrings")

    def test_operational_values_are_not_config(self, tmp_path: Path) -> None:
        # 제한시간은 측정 조건이 아니다 - 바꿔도 이어 쓸 수 있어야 한다.
        path = tmp_path / "RUN.json"
        ao.record(path, dict(self.FIELDS))
        assert ao.record(path, dict(self.FIELDS) | {"timeout_s": "600"}) == []

    def test_more_runs_resume_and_leave_a_session(self, tmp_path: Path) -> None:
        """반복 횟수는 조건이 아니라 표본 크기다 - 1회 파일럿을 8회로 늘려 이어 쓴다."""
        path = tmp_path / "RUN.json"
        ao.record(path, dict(self.FIELDS) | {"runs": "1", "runner_sha": "aaa"})
        assert ao.record(path, dict(self.FIELDS) | {"runs": "8", "runner_sha": "bbb"}) == []
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["runs"] == "8"
        assert [(x["runs"], x["runner_sha"]) for x in data["sessions"]] == [
            ("1", "aaa"),
            ("8", "bbb"),
        ]

    def test_record_from_before_sessions_is_carried_over(self, tmp_path: Path) -> None:
        # 세션 기록이 생기기 전에 만든 RUN.json - 첫 세션을 아는 만큼 옮긴다.
        path = tmp_path / "RUN.json"
        legacy = dict(self.FIELDS) | {"runs": "1", "started_at": "2026-09-29T03:20:30Z"}
        path.write_text(json.dumps(legacy), encoding="utf-8")
        assert ao.record(path, dict(self.FIELDS) | {"runs": "8", "runner_sha": "bbb"}) == []
        first, second = json.loads(path.read_text(encoding="utf-8"))["sessions"]
        assert first == {"started_at": "2026-09-29T03:20:30Z", "runs": "1", "runner_sha": "unknown"}
        assert second["runs"] == "8"

    def test_model_description_survives_a_resume(self, tmp_path: Path) -> None:
        # 설명은 조건이 아니라 해석 당시의 기록이다. 이어 쓰는 세션은 모델을 다시
        # 해석하지 않아 빈 값을 넘기는데, 그게 거부도 덮어쓰기도 하면 안 된다.
        path = tmp_path / "RUN.json"
        note = "Frontier intelligence."
        ao.record(path, dict(self.FIELDS) | {"model_note": note})
        assert ao.record(path, dict(self.FIELDS) | {"model_note": ""}) == []
        assert json.loads(path.read_text(encoding="utf-8"))["model_note"] == note

    def test_refusal_leaves_the_record_untouched(self, tmp_path: Path) -> None:
        path = tmp_path / "RUN.json"
        ao.record(path, dict(self.FIELDS))
        before = path.read_text(encoding="utf-8")
        assert ao.record(path, dict(self.FIELDS) | {"model": "other"})
        assert path.read_text(encoding="utf-8") == before

    def test_cli_exit_code_is_3_on_mismatch(self, tmp_path: Path) -> None:
        path = tmp_path / "RUN.json"
        args = [f"{k}={v}" for k, v in self.FIELDS.items()]
        assert ao.main(["record", str(path), *args]) == 0
        assert ao.main(["record", str(path), *args, "model=other"]) == 3


class TestAudit:
    """상자 밖 접근 흔적. 상자 자신의 절대경로는 흔적이 아니다."""

    BOX = "/var/folders/ab/T/tmp.XYZ"

    def _codex(self, tmp_path: Path, *commands: str) -> Path:
        raw = tmp_path / "raw"
        raw.mkdir()
        events = [
            json.dumps({"type": "item.completed",
                        "item": {"type": "command_execution", "command": c}})
            for c in commands
        ]
        (raw / "S.0.a0.jsonl").write_text("\n".join(events) + "\n", encoding="utf-8")
        (raw / "S.0.a0.box").write_text(self.BOX + "\n", encoding="utf-8")
        return tmp_path

    def test_inside_the_box_is_clean(self, tmp_path: Path) -> None:
        out = self._codex(
            tmp_path,
            "/bin/zsh -lc 'nl -ba module.py'",
            f"/bin/zsh -lc 'sed -n 1,40p {self.BOX}/module.py'",
            f"/bin/zsh -lc 'cat /private{self.BOX}/module.py'",
            "/bin/zsh -lc \"rg -n 'def ...' module.py\"",
        )
        assert ao.audit(out) == {}

    @pytest.mark.parametrize(
        "command",
        [
            "/bin/zsh -lc 'ls ..'",
            "/bin/zsh -lc 'cat ../meta.toml'",
            "/bin/zsh -lc 'find / -name module.py'",
            "/bin/zsh -lc 'ls ~/Documents'",
            "/bin/zsh -lc 'cat /Users/x/codeproof-ai/corpus/decoys/D001/meta.toml'",
            "/bin/zsh -lc 'ls /var/folders/ab/T/'",
        ],
    )
    def test_outside_the_box_is_flagged(self, tmp_path: Path, command: str) -> None:
        hits = ao.audit(self._codex(tmp_path, command))
        assert list(hits) == ["S.0.a0.jsonl"], command

    def test_claude_denials_are_flagged(self, tmp_path: Path) -> None:
        raw = tmp_path / "raw"
        raw.mkdir()
        denied = _envelope(permission_denials=[{"tool_name": "Read", "path": "/etc"}])
        (raw / "S.0.a0.claude.json").write_text(json.dumps(denied), encoding="utf-8")
        (raw / "T.0.a0.claude.json").write_text(json.dumps(_envelope()), encoding="utf-8")
        assert list(ao.audit(tmp_path)) == ["S.0.a0.claude.json"]

    def test_unreadable_denials_are_flagged(self, tmp_path: Path) -> None:
        """경계 - 목록이 아닌 거부 기록은 그 자체가 흔적이다 (읽다 죽지 않는다)."""
        raw = tmp_path / "raw"
        raw.mkdir()
        odd = _envelope(permission_denials=True)
        (raw / "S.0.a0.claude.json").write_text(json.dumps(odd), encoding="utf-8")
        assert ao.audit(tmp_path) == {"S.0.a0.claude.json": ["true"]}


class TestCodexFailureCause:
    """[실측] 크레딧 소진이 「findings 를 찾지 못했다」로만 보였다 - 원인을 올린다."""

    EVENTS = "\n".join([
        json.dumps({"type": "thread.started"}),
        json.dumps({"type": "error", "message": "Your workspace is out of credits."}),
        json.dumps(
            {"type": "turn.failed", "error": {"message": "Your workspace is out of credits."}}
        ),
    ])

    def test_error_event_becomes_the_reason(self) -> None:
        with pytest.raises(ao.RefusedError, match="codex 오류: Your workspace is out of credits"):
            ao.extract_codex("", self.EVENTS)

    def test_valid_answer_ignores_old_errors(self) -> None:
        payload, _ = ao.extract_codex(json.dumps({"findings": []}), self.EVENTS)
        assert payload == {"findings": []}


class TestLastFindingsObject:
    def test_prompt_echo_does_not_win(self) -> None:
        # 규격 예시도 {"findings": [...]} 모양이다 - 마지막 것이 답이다.
        text = 'echo {"findings": [{"file": "x"}]} ... answer: {"findings": []}'
        assert ao.last_findings_object(text) == {"findings": []}

    def test_none_when_absent(self) -> None:
        assert ao.last_findings_object("no json here") is None


class TestRunnerNeedsTheDocstringKnob:
    """🔴 손잡이 이전의 내보내기로 돌리면 빈 값이 기록되어 keep 과 neutral 이 같은 설정이 된다.

    실행기를 진짜 에이전트 없이 돌린다 - 가짜 `claude` 는 아무것도 하지 않는다 (DESIGN §7.10c).
    """

    RUNNER = SCRIPT.parent / "review-with-agent.sh"

    def _run(self, tmp_path: Path, manifest: dict[str, object]) -> subprocess.CompletedProcess[str]:
        export = tmp_path / "export"
        export.mkdir(exist_ok=True)
        (export / "PROMPT.md").write_text("p\n", encoding="utf-8")
        (export / "SCHEMA.json").write_text("{}\n", encoding="utf-8")
        (export / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        fake.chmod(0o755)
        env = os.environ | {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        return subprocess.run(
            ["bash", str(self.RUNNER), "claude", str(export), str(tmp_path / "out"),
             "--effort", "low"],
            capture_output=True, text=True, env=env, timeout=60, check=False,
        )

    def test_an_export_without_sample_digests_is_refused(self, tmp_path: Path) -> None:
        """🔴 지문 없는 내보내기로 돌면 출력마다 잰 코드를 모른다 - pack 이 전부 거부할 실행이다."""
        (tmp_path / "export" / "D001").mkdir(parents=True)
        r = self._run(tmp_path, {"prompt_hash": "p", "docstrings": "neutral", "samples": []})
        assert r.returncode == 2
        assert "샘플 지문이 없다" in r.stderr

    def test_an_export_with_sample_digests_gets_past_the_check(self, tmp_path: Path) -> None:
        """대조군 - 지문이 있으면 다음 단계(CLI 판 확인)에서 멈춘다."""
        (tmp_path / "export" / "D001").mkdir(parents=True)
        rows = [{"sample_id": "D001", "digest": "a" * 64}]
        r = self._run(tmp_path, {"prompt_hash": "p", "docstrings": "neutral", "samples": rows})
        assert "샘플 지문이 없다" not in r.stderr
        assert "버전을 읽지 못했다" in r.stderr

    def test_an_export_without_the_knob_is_refused(self, tmp_path: Path) -> None:
        r = self._run(tmp_path, {"prompt_hash": "p"})
        assert r.returncode == 2
        assert "docstrings 가 없다" in r.stderr

    def test_an_export_with_the_knob_gets_past_the_check(self, tmp_path: Path) -> None:
        """대조군 - 손잡이가 있으면 이 검사를 지나 다음 단계(CLI 판 확인)에서 멈춘다."""
        r = self._run(tmp_path, {"prompt_hash": "p", "docstrings": "neutral"})
        assert r.returncode != 0
        assert "docstrings 가 없다" not in r.stderr
        assert "버전을 읽지 못했다" in r.stderr, "가짜 claude 가 판을 내지 않으니 거기서 멈춘다"
