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
import json, os, sys, time
args = sys.argv[1:]
if args == ["--version"]:
    print("0.63.0"); sys.exit(0)
mode = os.environ.get("FAKE_GEMINI_MODE", "ok")
prompt = args[args.index("-p") + 1]
stage = "probe" if "single word" in prompt else "review"
# 실패 모드는 한 단계에서만 - 모델 확인에서 멈추면 샘플마다의 판정은 한 번도 돌지 않는다
if mode in ("blocked", "other-model", "hang") and stage != os.environ.get("FAKE_GEMINI_STAGE"):
    mode = "ok"
settings_path = os.environ.get("GEMINI_CLI_SYSTEM_SETTINGS_PATH", "")
home = os.environ.get("HOME", "")
login = os.path.join(home, ".gemini", "oauth_creds.json")
with open(os.environ["FAKE_GEMINI_LOG"], "a") as log:
    log.write(json.dumps({
        "args": args, "stage": stage, "home": home, "cwd": os.getcwd(),
        "settings": json.load(open(settings_path)) if settings_path else None,
        "settings_dir_mode": oct(os.stat(os.path.dirname(settings_path)).st_mode & 0o777),
        "login_is_link": os.path.islink(login),
        "files": sorted(os.listdir(".")),
    }) + "\n")
if mode == "hang":
    time.sleep(10)  # 제한(3초)보다 길다 - 끊기지 않으면 아래에서 정상 답을 내 지적이 써진다
model = args[args.index("-m") + 1]
def emit(**e): print(json.dumps(e))
emit(type="init", session_id="s", model=model)
emit(type="message", role="user", content=prompt[:20])
if mode == "blocked":
    # 막히기 전 조각과 고정한 모델의 토큰이 있다 - 막힘을 가르는 것은 result 의 status 뿐이다
    emit(type="message", role="assistant", content='{"findings": []}', delta=True)
    emit(type="error", severity="error", message="OTHER_BLOCKED")
    emit(type="result", status="error", error={"type": "INVALID_STREAM", "message": "blocked"},
         stats={"models": {model: {"output_tokens": 3, "input_tokens": 100}}})
    sys.exit(1)
emit(type="message", role="assistant", content='{"findings": [{"note": "도구 전 말"}]}', delta=True)
path = "/etc/passwd" if mode == "escape" else os.path.join(os.getcwd(), "module.py")
emit(type="tool_use", tool_name="read_file", tool_id="t1", parameters={"file_path": path})
emit(type="tool_result", tool_id="t1", status="success", output="...")
answer = {"findings": [{"file": "module.py", "line": 1, "severity": "warning",
                        "category": "correctness", "message": "m", "quoted_code": "x = 1"}]}
text = "ok" if stage == "probe" else json.dumps(answer)
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


def _path_without(tmp_path: Path, name: str) -> str:
    """PATH 에서 명령 하나만 뺀 디렉터리 - 나머지 도구는 그대로 보인다 (timeout 없는 맥처럼)."""
    shadow = tmp_path / "path"
    shadow.mkdir()
    for d in os.environ["PATH"].split(os.pathsep):
        if not d or not Path(d).is_dir():
            continue
        for entry in Path(d).iterdir():
            link = shadow / entry.name
            if entry.name != name and not link.exists(follow_symlinks=False):
                link.symlink_to(entry.absolute())
    return str(shadow)


GLOBAL = r'''#!/usr/bin/env python3
import json, os
with open(os.environ["FAKE_GEMINI_LOG"], "a") as log:
    log.write(json.dumps({"stage": "GLOBAL", "cwd": os.getcwd()}) + "\n")
raise SystemExit(1)
'''
"""PATH 뒤쪽의 다른 설치 - 불리면 기록하고 실패한다 (자동 업데이트되는 전역 CLI 의 자리)."""


def _run(
    tmp_path: Path, *, mode: str = "ok", stage: str = "review", effort: str = "low",
    login: bool = True, without_timeout: bool = False, limit_s: int | None = None,
    extra: tuple[str, ...] = (), relative: bool = False,
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
    path = _path_without(tmp_path, "timeout") if without_timeout else os.environ["PATH"]
    if without_timeout:
        assert shutil.which("timeout", path=path) is None, "남아 있으면 대체 경로를 시험하지 못한다"
    first = str(bin_dir)
    if relative:  # 🔴 고정 CLI 를 저장소 기준 상대 경로로 - 상자(cwd)에서는 풀리지 않는다
        other = tmp_path / "global"
        other.mkdir()
        (other / "gemini").write_text(GLOBAL, encoding="utf-8")
        (other / "gemini").chmod(0o755)
        first = f"{bin_dir.name}{os.pathsep}{other}"
    env = os.environ | {
        "PATH": f"{first}{os.pathsep}{path}", "HOME": str(home),
        "FAKE_GEMINI_MODE": mode, "FAKE_GEMINI_STAGE": stage, "FAKE_GEMINI_LOG": str(log),
    }
    limit = ["--timeout", str(limit_s)] if limit_s else []
    r = subprocess.run(
        ["bash", str(RUNNER), "gemini", str(_export(tmp_path)), str(tmp_path / "out"),
         "--effort", effort, "--model", MODEL, *limit, *extra],
        capture_output=True, text=True, env=env, timeout=40 if limit_s else 120, check=False,
        cwd=tmp_path,
    )
    return r, log


def _calls(log: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


def _reviews(log: Path) -> int:
    """샘플 리뷰 호출 수 - 모델 확인 호출은 세지 않는다."""
    return sum(c["stage"] == "review" for c in _calls(log)) if log.exists() else 0


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

    def test_a_relative_cli_path_still_calls_the_pinned_cli(self, tmp_path: Path) -> None:
        """🔴 [실측] PATH 의 상대 항목은 저장소 cwd 에서 판을 확인하고 상자 cwd 에서는 다음 항목의
        전역 CLI 로 풀렸다 - RUN.json 의 판과 실제로 리뷰한 CLI 가 달랐다. 시작 때 절대 경로로
        고정한다."""
        r, log = _run(tmp_path, relative=True)
        assert r.returncode == 0, r.stderr
        calls = _calls(log)
        assert "GLOBAL" not in {c["stage"] for c in calls}
        assert len(calls) == 1 + len(SAMPLES), "해석 한 번 + 샘플마다 리뷰 한 번 - 전부 고정 CLI"

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

    @pytest.mark.parametrize("stage", ["probe", "review"])
    def test_an_answer_from_another_model_is_a_failure(self, tmp_path: Path, stage: str) -> None:
        """🔴 고정한 모델이 답하지 않았으면 측정 대상이 바뀐 것이다 (claude 와 같은 규칙).

        단계마다 본다 - [실측] 모델 확인에서만 어긋나게 했던 판은 샘플 리뷰를 한 번도 부르지 않았다.
        """
        r, log = _run(tmp_path, mode="other-model", stage=stage)
        assert "고정한 모델이 답하지 않았다" in r.stderr + r.stdout
        assert not (tmp_path / "out" / "S1.0.json").exists()
        assert _reviews(log) == (len(SAMPLES) if stage == "review" else 0)
        assert (r.returncode == 2) is (stage == "probe"), "확인에서 어긋나면 리뷰를 시작하지 않는다"

    def test_a_blocked_answer_is_not_zero_findings(self, tmp_path: Path) -> None:
        """🔴 막히기 전 조각에 findings 가 있어도 status 가 error 면 실패다 - 지적 0건이 아니다.

        [실측] 모델 확인에서 막히던 판은 샘플 리뷰를 한 번도 부르지 않고도 통과했다 (macOS CI 에서
        실행기가 시작하자마자 멈췄을 때도 통과했다).
        """
        r, log = _run(tmp_path, mode="blocked")
        assert _reviews(log) == len(SAMPLES), "샘플 리뷰에서 막혀야 이 경로를 시험한다"
        assert not (tmp_path / "out" / "S1.0.json").exists(), "막힌 답을 지적 0건으로 쓰지 않는다"
        assert "gemini 실패" in r.stdout

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

    def test_without_gnu_timeout_the_review_still_runs(self, tmp_path: Path) -> None:
        """🔴 맥 기본 상태에는 timeout 이 없다 [실측: CI macOS].

        면접관 경로(codeproof review --agent)가 이 실행기를 부른다 - coreutils 를 요구하지 않는다.
        """
        r, _ = _run(tmp_path, without_timeout=True)
        assert r.returncode == 0, r.stderr
        out = json.loads((tmp_path / "out" / "S1.0.json").read_text(encoding="utf-8"))
        assert [f["message"] for f in out["findings"]] == ["m"]

    @pytest.mark.parametrize(("extra", "shown", "progress"), [
        (("--blind",), "리뷰 완료", "blind"),
        ((), "지적 1", "counts"),
    ])
    def test_blind_progress_hides_the_counts(
        self, tmp_path: Path, extra: tuple[str, ...], shown: str, progress: str,
    ) -> None:
        """🔴 측정 중에는 결과를 보지 않는다 - 진행 줄에 지적 수가 없고 세션에 남는다 (§7.10d).

        손잡이가 없는 쪽은 대조군이다 - 고른 줄이 진행 줄이 맞고, 거기에 지적 수가 보인다.
        """
        r, _ = _run(tmp_path, extra=extra)
        assert r.returncode == 0, r.stderr
        lines = [line for line in r.stdout.splitlines() if line.lstrip().startswith("[")]
        assert len(lines) == len(SAMPLES)
        assert all(shown in line for line in lines)
        assert all(("지적" in line) is (progress == "counts") for line in lines)
        record = json.loads((tmp_path / "out" / "RUN.json").read_text(encoding="utf-8"))
        assert record["sessions"][-1]["progress"] == progress

    def test_the_fallback_still_ends_a_hung_call(self, tmp_path: Path) -> None:
        """대체 경로도 제한시간을 지킨다 - 10초 걸리는 호출이 3초에 끊겨 지적을 쓰지 못한다.

        상한이 없으면 호출이 끝나 지적이 써진다 - 깨진 경우를 시간 초과까지 기다리지 않고 잡는다.
        """
        r, log = _run(tmp_path, mode="hang", without_timeout=True, limit_s=3)
        assert _reviews(log) == len(SAMPLES), "호출은 시작됐다 - 부르기 전에 실패한 것이 아니다"
        assert not (tmp_path / "out" / "S1.0.json").exists()
        assert "실패 2" in r.stdout

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
