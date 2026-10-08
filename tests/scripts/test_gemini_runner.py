"""review-with-agent.sh 의 gemini 경로 - 진짜 CLI · 로그인 없이 깨뜨려 본다 (H3).

가짜 `gemini` 는 받은 인자 · HOME · 시스템 설정을 기록하고, 0.63.0 번들이 내는 stream-json
모양(init · message · tool_use · result 의 stats.models)을 그대로 낸다 [소스: 번들의 emitEvent].
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parents[2] / "scripts" / "review-with-agent.sh"
MODEL = "gemini-test-pro"

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
if args == ["--version"]:
    print("0.63.0"); sys.exit(0)
mode = os.environ.get("FAKE_GEMINI_MODE", "ok")
settings_path = os.environ.get("GEMINI_CLI_SYSTEM_SETTINGS_PATH", "")
home = os.environ.get("HOME", "")
login = os.path.join(home, ".gemini", "oauth_creds.json")
with open(os.environ["FAKE_GEMINI_LOG"], "a") as log:
    log.write(json.dumps({
        "args": args, "home": home, "cwd": os.getcwd(),
        "settings": json.load(open(settings_path)) if settings_path else None,
        "settings_dir_mode": oct(os.stat(os.path.dirname(settings_path)).st_mode & 0o777),
        "login_is_link": os.path.islink(login),
        "files": sorted(os.listdir(".")),
    }) + "\n")
model = args[args.index("-m") + 1]
def emit(**e): print(json.dumps(e))
emit(type="init", session_id="s", model=model)
emit(type="message", role="user", content=args[args.index("-p") + 1][:20])
if mode == "blocked":
    emit(type="error", severity="error", message="OTHER_BLOCKED")
    emit(type="result", status="error", error={"type": "INVALID_STREAM", "message": "blocked"},
         stats={"models": {}})
    sys.exit(1)
emit(type="message", role="assistant", content='{"findings": [{"note": "도구 전 말"}]}', delta=True)
path = "/etc/passwd" if mode == "escape" else os.path.join(os.getcwd(), "module.py")
emit(type="tool_use", tool_name="read_file", tool_id="t1", parameters={"file_path": path})
emit(type="tool_result", tool_id="t1", status="success", output="...")
answer = {"findings": [{"file": "module.py", "line": 1, "severity": "warning",
                        "category": "correctness", "message": "m", "quoted_code": "x = 1"}]}
text = "ok" if "single word" in args[args.index("-p") + 1] else json.dumps(answer)
half = len(text) // 2
emit(type="message", role="assistant", content=text[:half], delta=True)
emit(type="message", role="assistant", content=text[half:], delta=True)
answered = "gemini-other-flash" if mode == "other-model" else model
emit(type="result", status="success", stats={"tool_calls": 1, "models": {
    answered: {"output_tokens": 12, "input_tokens": 100},
    "gemini-2.5-flash-lite": {"output_tokens": 0, "input_tokens": 5},
}})
'''


SAMPLES = ("S1", "S2")
"""둘이어야 HOME 을 샘플끼리 나눠 쓰는지 보인다 - 하나면 나눠 써도 통과한다."""


def _export(root: Path) -> Path:
    export = root / "export"
    for sid in SAMPLES:
        (export / sid).mkdir(parents=True)
        (export / sid / "module.py").write_text("x = 1\n", encoding="utf-8")
    (export / "PROMPT.md").write_text("review module.py\n", encoding="utf-8")
    (export / "SCHEMA.json").write_text("{}\n", encoding="utf-8")
    manifest = {
        "prompt_hash": "p", "instruction_hash": "i", "schema_hash": "s", "docstrings": "neutral",
        "samples": [{"sample_id": sid, "digest": "a" * 64} for sid in SAMPLES],
    }
    (export / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return export


def _run(
    tmp_path: Path, *, mode: str = "ok", effort: str = "low", login: bool = True,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    bin_dir, home = tmp_path / "bin", tmp_path / "home"
    bin_dir.mkdir(exist_ok=True)
    (home / ".gemini").mkdir(parents=True, exist_ok=True)
    if login:
        (home / ".gemini" / "oauth_creds.json").write_text("{}", encoding="utf-8")
    fake = bin_dir / "gemini"
    fake.write_text(FAKE, encoding="utf-8")
    fake.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    env = os.environ | {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "HOME": str(home),
        "FAKE_GEMINI_MODE": mode, "FAKE_GEMINI_LOG": str(log),
    }
    r = subprocess.run(
        ["bash", str(RUNNER), "gemini", str(_export(tmp_path)), str(tmp_path / "out"),
         "--effort", effort, "--model", MODEL],
        capture_output=True, text=True, env=env, timeout=120, check=False,
    )
    return r, log


def _calls(log: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


class TestGeminiRunner:
    def test_a_review_comes_back_as_findings(self, tmp_path: Path) -> None:
        r, _ = _run(tmp_path)
        assert r.returncode == 0, r.stderr
        out = json.loads((tmp_path / "out" / "S1.0.json").read_text(encoding="utf-8"))
        assert [f["message"] for f in out["findings"]] == ["m"], "도구 전의 말이 아니라 끝 답"
        record = json.loads((tmp_path / "out" / "RUN.json").read_text(encoding="utf-8"))
        assert record["agent"] == "gemini"
        assert record["model"] == MODEL
        assert "tools=read_file,grep_search,glob" in record["permission"]

    def test_each_call_is_isolated_from_the_users_home(self, tmp_path: Path) -> None:
        """🔴 사용자 설정 · 확장 · 기억을 싣지 않는다 - 로그인 파일만 링크한 새 HOME 이다."""
        _, log = _run(tmp_path)
        calls = _calls(log)
        assert len(calls) == 1 + len(SAMPLES), "해석 한 번 + 샘플마다 리뷰 한 번"
        homes = {c["home"] for c in calls}
        assert str(tmp_path / "home") not in homes
        assert len(homes) == len(calls), "🔴 HOME 을 호출끼리 나누지 않는다 (기억 도구가 쓴다)"
        for c in calls:
            assert c["login_is_link"], "로그인은 복사하지 않고 링크한다"
            assert c["settings_dir_mode"] == "0o700", "권한이 넓은 폴더의 시스템 설정은 무시된다"

    def test_the_measurement_conditions_are_forced(self, tmp_path: Path) -> None:
        _, log = _run(tmp_path)
        review = _calls(log)[-1]
        args = review["args"]
        assert isinstance(args, list)
        for flag in ("--approval-mode", "plan", "--skip-trust", "-o", "stream-json", "-m", MODEL):
            assert flag in args
        settings = review["settings"]
        assert isinstance(settings, dict)
        assert settings["tools"]["core"] == ["read_file", "grep_search", "glob"]
        override = settings["modelConfigs"]["overrides"][0]
        assert override["match"]["model"] == MODEL
        level = override["modelConfig"]["generateContentConfig"]["thinkingConfig"]["thinkingLevel"]
        assert level == "LOW", "effort low 는 thinkingLevel LOW 다 (D4)"
        assert settings["security"]["auth"]["selectedType"] == "oauth-personal"
        assert review["files"] == ["module.py"], "상자에는 제시된 파일만 있다 (C1)"

    def test_an_answer_from_another_model_is_a_failure(self, tmp_path: Path) -> None:
        """🔴 고정한 모델이 답하지 않았으면 측정 대상이 바뀐 것이다 (claude 와 같은 규칙)."""
        r, _ = _run(tmp_path, mode="other-model")
        assert r.returncode != 0
        assert "고정한 모델이 답하지 않았다" in r.stderr + r.stdout
        assert not (tmp_path / "out" / "S1.0.json").exists()

    def test_a_blocked_answer_is_not_zero_findings(self, tmp_path: Path) -> None:
        r, _ = _run(tmp_path, mode="blocked")
        assert r.returncode != 0
        assert not (tmp_path / "out" / "S1.0.json").exists(), "막힌 답을 지적 0건으로 쓰지 않는다"

    @pytest.mark.parametrize(("mode", "files"), [("ok", 0), ("escape", 1 + len(SAMPLES))])
    def test_reading_outside_the_box_is_audited(
        self, tmp_path: Path, mode: str, files: int,
    ) -> None:
        """상자 안 경로는 세지 않고 밖은 센다 - 모델 확인 호출도 같은 규칙이다."""
        r, _ = _run(tmp_path, mode=mode)
        record = json.loads((tmp_path / "out" / "RUN.json").read_text(encoding="utf-8"))
        audit = json.loads(record["audit"]) if isinstance(record["audit"], str) else record["audit"]
        assert audit["files"] == files, r.stdout
        assert ("/etc/passwd" in json.dumps(audit["hits"])) is (files > 0)

    def test_without_timeout_it_says_how_to_get_it(self, tmp_path: Path) -> None:
        """🔴 macOS 에는 timeout 이 없다 [실측: /usr/bin/timeout 없음] - 원인이 가려져 실패한다."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        for tool in ("python3", "dirname"):
            found = shutil.which(tool)
            assert found
            (bin_dir / tool).symlink_to(found)
        fake = bin_dir / "gemini"
        fake.write_text(FAKE, encoding="utf-8")
        fake.chmod(0o755)
        r = subprocess.run(
            ["/bin/bash", str(RUNNER), "gemini", str(_export(tmp_path)), str(tmp_path / "out"),
             "--effort", "low", "--model", MODEL],
            capture_output=True, text=True, env={"PATH": str(bin_dir), "HOME": str(tmp_path)},
            timeout=60, check=False,
        )
        assert r.returncode == 2
        assert "timeout 을 찾을 수 없다" in r.stderr

    def test_without_a_login_it_stops_and_says_so(self, tmp_path: Path) -> None:
        r, log = _run(tmp_path, login=False)
        assert r.returncode == 2
        assert "로그인돼 있지 않다" in r.stderr
        assert not log.exists(), "로그인 없이 CLI 를 부르지 않는다"

    @pytest.mark.parametrize("effort", ["medium", "max"])
    def test_an_effort_the_cli_cannot_set_is_refused(self, tmp_path: Path, effort: str) -> None:
        """thinkingLevel 은 LOW · HIGH 뿐이다 [소스: 0.63.0 번들] - 다른 값으로 바꾸지 않는다."""
        r, _ = _run(tmp_path, effort=effort)
        assert r.returncode == 2
        assert "low · high 뿐이다" in r.stderr
