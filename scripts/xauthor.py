"""codex 가 쓴 쌍 (DESIGN §7.10d) - 상자 · 격리 점검 · 카나리.

    python scripts/xauthor.py check                  격리 점검 - 모델을 부르지 않는다
    python scripts/xauthor.py canary <출력>           첫 exec - 🔴 유료 (codex 크레딧 · 호출 한 번)
    python scripts/xauthor.py canary <출력> --audit   감사 exec 그대로 (스키마 포함) - 🔴 유료

🔴 프로필 · 환경 · 플래그는 이 파일 한 곳에 둔다 - 선언의 「저자」 · 「상자」 행과 같다.
   바꾸면 다른 실행이다.
🔴 상자와 venv 는 저장소 · 홈 · /private/tmp · $TMPDIR 밖(/Users/Shared)에 만들고 끝나면 지운다.
🔴 카나리의 원본 이벤트에는 로컬 경로가 든다 - `runs/` 아래에 두고 경로를 가린 요약만 공개한다.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
CODEX = Path("/Users/Shared/xauthor-tools/codex-0.158.0/node_modules/.bin/codex")
"""저장소 밖에 둔다 (수집 전 수정 ⑦).

codex 는 자기 번들 zsh 경로를 읽기 허용에 더해 모델에게 보여 준다 - 저장소 안이면 그 경로로
저장소 이름이 모델 입력에 실린다 [실측 · 카나리]. 측정에 쓴 runs/tools 판의 사본이다 (sha256 같음).
"""
CODEX_VERSION = "codex-cli 0.158.0"
MODEL = "gpt-6-astra"
EFFORT = "high"
PYTHON = Path("/opt/homebrew/bin/python3.14")
SHARED = Path("/Users/Shared")
GATE_PAIR = "D115"
"""점검 · 카나리가 상자 안에서 관문을 돌려 보는 쌍 - tests/eval/test_gate.py 의 기준 쌍이다."""
OUTSIDE = (Path("/private/var/tmp/xauthor-probe"), SHARED / "xauthor-probe-outside")
"""상자 밖 쓰기 시도 - 쓰이면 새는 것이다. 이번 실행이 만든 것만 지운다."""
EXEC_TIMEOUT_S = 30 * 60  # 세션 상한 30분 (선언)
USAGE = 2


def profile(venv: Path) -> str:
    """허용 목록 프로필 - 선언의 「상자」 행 그대로 (venv 경로만 채운다)."""
    return (
        '{":root"="none", ":minimal"="read", "/opt/homebrew"="read", '
        f'"{venv}"="read", ":workspace_roots"="write", ":slash_tmp"="none", '
        '"/private/var/tmp"="none"}'
    )


def environment(box: Path, venv: Path) -> dict[str, str]:
    """최소 환경 - 띄운 세션의 변수(CLAUDE_CODE_* 등)를 물려주지 않는다."""
    return {
        "PATH": f"{venv}/bin:/usr/bin:/bin:/opt/homebrew/bin",
        "HOME": str(box / "home"),
        "TMPDIR": str(box / "tmp"),
        "CODEX_HOME": str(Path.home() / ".codex"),  # 인증을 복사하지 않는다 (수집 전 수정 ②)
        "LANG": "en_US.UTF-8",
    }


def exec_args(
    box: Path, venv: Path, prompt: str, last: Path, *, ephemeral: bool, schema: Path | None = None,
) -> list[str]:
    """저자 · 감사 · 카나리가 같이 쓰는 exec - 카나리만 세션 기록을 남긴다 (선언 「상자」 행).

    감사만 `--output-schema` 를 더한다 - 플래그 하나가 권한 프로필을 덮을 수 있어 (⑥)
    감사도 그 인자 그대로 카나리를 돈다.

    로그인 셸을 끈다 (수집 전 수정 ⑤) - codex 는 명령을 `zsh -lc` 로 돌리고 [실측 · 원본 426건],
    로그인 셸의 path_helper 가 venv 를 /usr/bin 뒤로 밀어 `python3` 가 시스템 판이 된다 [실측].
    🔴 `--sandbox` 를 주지 않는다 (수집 전 수정 ⑥) - 주면 프로필 대신 옛 workspace-write 가 걸린다
    [실측: 머리말 `[workdir, /tmp, $TMPDIR]` · 빼면 `[workdir]`]. 오류도 경고도 없다.
    """
    args = [
        str(CODEX), "exec", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
        "--color", "never", "-C", str(box),
        "-m", MODEL, "-c", f'model_reasoning_effort="{EFFORT}"', "-c", 'approval_policy="never"',
        "-c", "allow_login_shell=false",
        "-c", 'default_permissions="box"', "-c", f"permissions.box.filesystem={profile(venv)}",
        "--json", "-o", str(last),
    ]
    if ephemeral:
        args.insert(2, "--ephemeral")
    if schema is not None:
        args += ["--output-schema", str(schema)]
    return [*args, prompt]


def _tool(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        msg = f"{name} 을 찾지 못했다"
        raise FileNotFoundError(msg)
    return found


def _run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)  # noqa: S603


def build_wheel(out: Path) -> Path:
    done = _run([_tool("uv"), "build", "--wheel", "--out-dir", str(out)], cwd=REPO)
    if done.returncode:
        raise RuntimeError(done.stderr)
    return next(out.glob("codeproof_ai-*.whl"))


def make_box(tag: str, *, wheel: Path) -> tuple[Path, Path]:
    """상자(쓰기)와 venv(읽기만) - venv 에는 저장소에서 빌드한 wheel 을 비편집으로 깐다."""
    box = Path(tempfile.mkdtemp(prefix=f"xauthor-box-{tag}-", dir=SHARED))
    venv = Path(tempfile.mkdtemp(prefix=f"xauthor-venv-{tag}-", dir=SHARED))
    try:
        for sub in ("tmp", "home", "corpus"):
            (box / sub).mkdir()
        python = str(venv / "bin" / "python")
        for cmd in (
            [str(PYTHON), "-m", "venv", str(venv)],
            [_tool("uv"), "pip", "install", "--quiet", "--python", python, str(wheel)],
        ):
            if (done := _run(cmd)).returncode:
                raise RuntimeError(done.stderr)
    except BaseException:
        remove(box, venv)
        raise
    return box, venv


def seed_gate_pair(box: Path) -> None:
    """관문을 돌려 볼 쌍 하나 - 점검 · 카나리 상자에만 넣는다 (저자 상자에는 넣지 않는다)."""
    src = next((REPO / "corpus" / "decoys").glob(f"{GATE_PAIR}-*"))
    shutil.copytree(src, box / "corpus" / src.name, ignore=shutil.ignore_patterns("__pycache__"))


def remove(*paths: Path) -> None:
    for p in paths:
        shutil.rmtree(p, ignore_errors=True)


def _remove_outside(before: set[Path]) -> None:
    for p in OUTSIDE:
        if p not in before:
            p.unlink(missing_ok=True)


def _codex_version() -> str:
    return _run([str(CODEX), "--version"]).stdout.strip() if CODEX.exists() else ""


def _user_tmpdir() -> Path:
    """사용자 임시 폴더 - 띄운 세션의 $TMPDIR 은 다른 곳일 수 있어 OS 에 묻는다."""
    if getconf := shutil.which("getconf"):
        done = _run([getconf, "DARWIN_USER_TEMP_DIR"])
        if done.returncode == 0 and done.stdout.strip():
            return Path(done.stdout.strip())
    return Path(tempfile.gettempdir())


# ── 점검표 - 점검(모델 없이)과 카나리(첫 exec)가 같은 표를 쓴다 ─────────────────


def probes(
    box: Path,
    venv: Path,
    *,
    repo: Path = REPO,
    home: Path | None = None,
    user_tmp: Path | None = None,
) -> list[tuple[str, str, bool]]:
    """(이름, 셸 조각, 되어야 하는가). 저장소 · 홈 · 사용자 임시 폴더는 시험에서 바꿔 넣는다.

    따옴표와 `$` 를 쓰지 않는다 - 카나리는 「시킨 명령이 보고된 명령에 그대로 있는가」로
    판정하는데, codex 는 명령을 홑따옴표로 감싸 보고하고 홑따옴표가 든 명령만 겹따옴표로
    감싼다 [실측 · 원본 426건]. `$` · 겹따옴표가 든 명령의 보고 모양은 본 적이 없다.
    """
    home = home or Path.home()
    user_tmp = user_tmp or _user_tmpdir()
    paths = (repo, home, user_tmp, box, venv, *OUTSIDE)
    if odd := [str(p) for p in paths if re.search(r"[\s'\"$\\]", str(p))]:
        msg = f"공백 · 따옴표 · $ 가 든 경로는 점검표에 쓸 수 없다: {odd}"
        raise ValueError(msg)
    var_tmp, shared = OUTSIDE
    return [
        ("REPO", f"cat {repo / 'README.md'}", False),
        ("USER-HOME", f"ls {home}", False),
        ("CODEX-HOME", f"ls {home / '.codex'}", False),
        ("SLASH-TMP", "ls /private/tmp", False),
        ("USER-TMPDIR", f"ls {user_tmp}", False),
        ("VAR-TMP", f"touch {var_tmp}", False),
        ("SHARED", f"touch {shared}", False),
        ("VENV-WRITE", f"touch {venv / 'probe'}", False),
        ("NET", "curl -s -m 5 -o /dev/null https://example.com", False),
        ("BOX-WRITE", "touch probe.txt", True),
        # macOS `mktemp -d` 는 $TMPDIR 이 아니라 사용자 임시 폴더로 간다 [실측] - 변수와 쓰기를 본다
        ("BOX-TMP", f"env | grep -qx TMPDIR={box / 'tmp'} && touch {box / 'tmp' / 'probe'}", True),
        ("VENV-FIRST", f"command -v python3 | grep -qx {venv / 'bin' / 'python3'}", True),
        ("GATE", "codeproof decoy gate --corpus corpus --race-runs 1", True),
    ]


def check_line(name: str, probe: str, allowed: bool) -> str:
    """되어야 하는 것은 되면 OK, 막혀야 하는 것은 되면 BAD 를 찍는다 - 표지는 한 줄이다."""
    good, bad = f"CANARY-OK-{name}", f"CANARY-BAD-{name}"
    yes, no = (good, bad) if allowed else (bad, good)
    return f"{probe} >/dev/null 2>&1 && echo {yes} || echo {no}"


def verdict_of(name: str, out: str) -> str:
    """BAD 표지가 있거나 OK 표지가 없으면 BAD - 아무것도 안 찍힌 것은 통과가 아니다."""
    lines = set(out.split("\n"))
    return "OK" if f"CANARY-OK-{name}" in lines and f"CANARY-BAD-{name}" not in lines else "BAD"


def _quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _world_writable() -> list[str]:
    cmd = [_tool("find"), "/", "-maxdepth", "4", "-type", "d", "-perm", "-0002"]
    skip = re.compile(r"^/(System/Volumes|dev)(/|$)")
    found = _run(cmd, timeout=300).stdout.split("\n")
    return sorted({d for d in found if d and not skip.match(d)})


def writable_lines(writable: list[str]) -> list[str]:
    """전 사용자 쓰기 가능 폴더마다 쓰기를 시도한다 - 시도 수를 같이 찍는다 (0이면 공허하다)."""
    name = f"xauthor-probe-{os.getpid()}"
    lines = ["n=0; w=0"]
    for d in writable:
        p = _quote(f"{d}/{name}")
        lines.append(
            f"n=$((n+1)); if touch {p} 2>/dev/null; then w=$((w+1)); "
            f"echo CANARY-BAD-WRITE {_quote(d)}; rm -f {p}; fi"
        )
    lines.append('echo "WRITABLE-TRIED $n WROTE $w"')
    return lines


def judge_check(out: str, table: list[tuple[str, str, bool]]) -> tuple[bool, str]:
    """(성립하는가, 한 줄 요약)."""
    bad = [name for name, _, _ in table if verdict_of(name, out) != "OK"]
    wrote = [ln.split(" ", 1)[1] for ln in out.split("\n") if ln.startswith("CANARY-BAD-WRITE ")]
    tried = re.search(r"^WRITABLE-TRIED (\d+) WROTE (\d+)$", out, flags=re.MULTILINE)
    n, w = (int(tried[1]), int(tried[2])) if tried else (0, 0)
    ok = not bad and not wrote and w == 0 and n > 0
    return ok, f"쓰기 가능 폴더 시도 {n} · 쓴 곳 {wrote or '없음'} · 기대와 다름 {bad or '없음'}"


def check() -> int:
    """선언의 격리가 이 기계에서 지금 성립하는가 - 기대와 다른 것이 하나라도 있으면 1.

    `codex sandbox` 는 모델을 부르지 않는다. 셸은 exec 와 같은 비로그인 zsh 다 (수집 전 수정 ⑤).
    """
    if (found := _codex_version()) != CODEX_VERSION:
        print(f"codex 판이 다르다: {found!r} (선언 {CODEX_VERSION})", file=sys.stderr)
        return USAGE
    before = {p for p in OUTSIDE if p.exists()}
    with tempfile.TemporaryDirectory() as build:
        box, venv = make_box("check", wheel=build_wheel(Path(build)))
    try:
        seed_gate_pair(box)
        table = probes(box, venv)
        lines = [*(check_line(*row) for row in table), *writable_lines(_world_writable())]
        cmd = [
            str(CODEX), "sandbox", "-c", f"permissions.box.filesystem={profile(venv)}",
            "-P", "box", "-C", str(box), "--", "/bin/zsh", "-c", "\n".join(lines),
        ]
        done = _run(cmd, env=environment(box, venv), stdin=subprocess.DEVNULL, timeout=600)
    finally:
        remove(box, venv)
        _remove_outside(before)
    ok, summary = judge_check(done.stdout, table)
    print(summary)
    return 0 if ok else 1


# ── 카나리 (첫 exec · 유료) ───────────────────────────────────────────────────


def canary_prompt(nonce: str, table: list[tuple[str, str, bool]], *, audit: bool = False) -> str:
    body = "\n".join(f"{i}. {check_line(*row)}" for i, row in enumerate(table, 1))
    last = "findings 가 빈 목록인 JSON 만" if audit else "DONE 한 단어만"
    return (
        "이것은 샌드박스 설정 점검이다. "
        "아래 명령을 적힌 그대로, 한 번에 하나씩 셸 도구로 실행하라. "
        "명령을 고치거나 합치거나 건너뛰지 마라. 실패해도 다음 명령으로 넘어간다. "
        f"모두 실행한 뒤 마지막 답으로 {last} 쓴다. 점검 표지: {nonce}\n\n{body}\n"
    )


def _executions(events: Path) -> list[dict[str, object]]:
    found = []
    for raw in events.read_text(encoding="utf-8").split("\n"):
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        item = ev.get("item") if isinstance(ev, dict) else None
        if (
            ev.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("type") == "command_execution"
        ):
            found.append(item)
    return found


def judge_canary(events: Path, table: list[tuple[str, str, bool]]) -> dict[str, str]:
    """명령마다 「OK」 · 「BAD」 · 「안 돌림」 - 시킨 명령이 그대로 없으면 안 돌린 것이다."""
    runs = _executions(events)
    verdict: dict[str, str] = {}
    for name, probe, _allowed in table:
        # 명령은 표지로도 가른다 - 경로 조각은 다른 명령에도 들어 있다 (홈 ⊂ ~/.codex)
        marker = re.compile(rf"CANARY-OK-{re.escape(name)}(?![\w-])")
        mine = [
            r for r in runs
            if probe in (cmd := str(r.get("command", ""))) and marker.search(cmd)
        ]
        out = "\n".join(str(r.get("aggregated_output", "")) for r in mine)
        verdict[name] = verdict_of(name, out) if mine else "안 돌림"
    return verdict


def _rollout(nonce: str, since: float) -> Path | None:
    root = Path.home() / ".codex" / "sessions"
    for p in sorted(root.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        if p.stat().st_mtime < since:
            break
        if nonce in p.read_text(encoding="utf-8", errors="replace"):
            return p
    return None


def _inputs(rollout: Path) -> list[tuple[str, dict[str, Any]]]:
    """모델이 받은 입력 - (종류, payload). session_meta · turn_context · 지시 메시지.

    도구 출력은 우리 명령의 결과라 뺀다 (막힌 경로를 적은 오류문에 저장소 이름이 들어간다).
    """
    found = []
    for raw in rollout.read_text(encoding="utf-8", errors="replace").split("\n"):
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        kind = rec.get("type")
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        role = payload.get("role")
        if kind in ("session_meta", "turn_context"):
            found.append((str(kind), payload))
        elif (
            kind == "response_item"
            and payload.get("type") == "message"
            and role in ("developer", "user", "system")
        ):
            found.append((str(role), payload))
    return found


def _entries(node: object) -> list[str]:
    """권한 목록의 (접근, 경로) - 모델에게 보여 준 파일 시스템 정책."""
    if isinstance(node, list):
        return [e for item in node for e in _entries(item)]
    if not isinstance(node, dict):
        return []
    if "access" in node and isinstance(node.get("path"), dict):
        where = node["path"].get("path") or json.dumps(node["path"], ensure_ascii=False)
        return [f"{node['access']} {where}"]
    return [e for value in node.values() for e in _entries(value)]


def input_inventory(rollout: Path, nonce: str, hide: dict[str, str]) -> list[str]:
    """카나리 지시 밖의 입력마다 한 줄 - 경로를 가려 공개 요약에 싣는다 (선언 「상자」 행).

    session_meta 는 키만 싣는다 - 계정 식별자(creator_*_id)가 든다 [실측 · 카나리].
    turn_context 는 키와 권한 목록을 싣는다.
    """
    lines = []
    for kind, payload in _inputs(rollout):
        text = json.dumps(payload, ensure_ascii=False)
        if nonce in text:
            continue
        if kind in ("session_meta", "turn_context"):
            line = f"{kind} ({len(text)}자): 키 {', '.join(sorted(payload))}"
            if kind == "turn_context":
                line += f" · 권한 {sorted(set(_entries(payload.get('permission_profile'))))}"
        else:
            content = payload.get("content")
            first = content[0] if isinstance(content, list) and content else content
            head = first.get("text", "") if isinstance(first, dict) else str(first)
            line = f"{kind} ({len(text)}자): {head[:120]}"
        for real, mask in hide.items():
            line = line.replace(real, mask)
        lines.append(line)
    return lines


def model_input_traces(rollout: Path, nonce: str) -> dict[str, int]:
    """모델이 받은 입력 중 우리 지시(표지가 든 메시지) 밖에 이 저장소의 흔적이 몇 번 있는가.

    codex 내장 지시(session_meta.base_instructions)만 뺀다 - 그 안의 일반 문장에
    'memory' 가 있다 [실측 · 카나리].
    """
    words = ("codeproof", "decoy", "twin", "memor")
    counts = dict.fromkeys(words, 0)
    for kind, payload in _inputs(rollout):
        text = json.dumps(payload, ensure_ascii=False)
        if nonce in text:
            continue
        if kind == "session_meta":
            rest = {k: v for k, v in payload.items() if k != "base_instructions"}
            text = json.dumps(rest, ensure_ascii=False)
        for w in words:
            counts[w] += text.lower().count(w)
    return counts


AUDIT_SCHEMA = REPO / "results" / "cross-family-audit" / "schema.json"


def canary(out: Path, *, audit: bool = False) -> int:
    """첫 exec - 기대와 다른 명령이 하나라도 있거나 모델 입력에 흔적이 있으면 1.

    `audit` 이면 감사 exec 그대로 돈다 (`--output-schema` 포함).
    """
    if (found := _codex_version()) != CODEX_VERSION:
        print(f"codex 판이 다르다: {found!r} (선언 {CODEX_VERSION})", file=sys.stderr)
        return USAGE
    out.mkdir(parents=True, exist_ok=True)
    before = {p for p in OUTSIDE if p.exists()}
    with tempfile.TemporaryDirectory() as build:
        box, venv = make_box("canary", wheel=build_wheel(Path(build)))
    rc, verdict, rollout, traces, inventory = -1, {}, None, None, []
    try:
        seed_gate_pair(box)
        table = probes(box, venv)
        nonce = f"xauthor-canary-{os.getpid()}-{int(time.time())}"
        started = time.time()
        prompt = canary_prompt(nonce, table, audit=audit)
        schema = AUDIT_SCHEMA if audit else None
        args = exec_args(box, venv, prompt, out / "canary.last.txt", ephemeral=False, schema=schema)
        with (
            (out / "canary.jsonl").open("w", encoding="utf-8") as ev,
            (out / "canary.err").open("w", encoding="utf-8") as err,
        ):
            rc = subprocess.run(  # noqa: S603 - 인자는 이 파일이 만든다
                args, stdout=ev, stderr=err, env=environment(box, venv),
                stdin=subprocess.DEVNULL, timeout=EXEC_TIMEOUT_S, check=False,
            ).returncode
        verdict = judge_canary(out / "canary.jsonl", table)
        rollout = _rollout(nonce, started - 5)
        if rollout:
            traces = model_input_traces(rollout, nonce)
            hide = {str(box): "<box>", str(venv): "<venv>", str(Path.home()): "~"}
            inventory = input_inventory(rollout, nonce, hide)
    finally:
        remove(box, venv)
        _remove_outside(before)
    home = str(Path.home())
    summary = {
        "codex": CODEX_VERSION, "model": MODEL, "effort": EFFORT, "audit": audit, "rc": rc,
        "verdict": verdict, "model_input_traces": traces, "model_input": inventory,
        "rollout": str(rollout).replace(home, "~") if rollout else None,
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    (out / "canary.summary.json").write_text(text, encoding="utf-8")
    bad = {k: v for k, v in verdict.items() if v != "OK"}
    print(f"rc={rc} · 기대와 다름 {bad or '없음'} · 모델 입력의 흔적 {traces}")
    clean = traces is not None and not any(traces.values())
    return 0 if verdict and not bad and clean else 1


def main(argv: list[str]) -> int:
    if argv == ["check"]:
        return check()
    if argv[:1] == ["canary"] and len(argv[1:]) == 1:
        return canary(Path(argv[1]))
    if argv[:1] == ["canary"] and argv[2:] == ["--audit"]:
        return canary(Path(argv[1]), audit=True)
    print(__doc__, file=sys.stderr)
    return USAGE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
