"""review-with-agent.sh 의 판정 로직 - 에이전트 없이 깨뜨려 본다 (H3).

계약은 두 줄이다: 정상은 통과하고, 위반은 **잡힌다**. 한 줄만 보면
`return` 하나로 끝나는 무능한 가드도 통과한다.
"""

from __future__ import annotations

import importlib.util
import json
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


class TestClaudeModelIsPinned:
    """🔴 고정한 모델이 아닌 모델이 답하면 측정 대상이 바뀐 것이다 (D5 fallbacks)."""

    def test_pinned_model_passes(self) -> None:
        payload, meta = ao.extract_claude(_envelope(), "claude-fable-5-1")
        assert payload["findings"] == [FINDING]
        assert "denials=0" in meta

    def test_substituted_model_is_refused(self) -> None:
        with pytest.raises(ao.RefusedError, match="고정한 모델이 답하지 않았다"):
            ao.extract_claude(_envelope("claude-opus-5-5"), "claude-fable-5-1")

    def test_error_envelope_is_refused(self) -> None:
        with pytest.raises(ao.RefusedError, match="is_error"):
            ao.extract_claude(_envelope(is_error=True), "claude-fable-5-1")

    def test_falls_back_to_result_text(self) -> None:
        env = _envelope(structured_output=None, result="산문 " + json.dumps({"findings": []}))
        payload, _ = ao.extract_claude(env, "claude-fable-5-1")
        assert payload == {"findings": []}


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

    def test_codex_pinned_model_must_exist(self) -> None:
        assert ao.resolve_codex(self.CATALOG, "low", "second") == "second"
        with pytest.raises(ao.RefusedError, match="없는 모델"):
            ao.resolve_codex(self.CATALOG, "low", "nope")


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

    def test_operational_values_are_not_config(self, tmp_path: Path) -> None:
        # 제한시간은 측정 조건이 아니다 - 바꿔도 이어 쓸 수 있어야 한다.
        path = tmp_path / "RUN.json"
        ao.record(path, dict(self.FIELDS))
        assert ao.record(path, dict(self.FIELDS) | {"timeout_s": "600"}) == []

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
