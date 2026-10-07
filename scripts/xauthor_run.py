"""codex 가 쌍을 쓰는 실행기 - DESIGN §7.10d 「시도 · 렌즈」 · 「1단계 · 타당성」.

    uv run python scripts/xauthor_run.py <출력>              🔴 유료 (codex 크레딧) - 첫 바퀴
    uv run python scripts/xauthor_run.py <출력> --summary    지금까지의 요약 (codex 없이)

첫 바퀴는 분류 이름순으로 한 쌍씩 쓴다. 출력 디렉터리의 파일이 상태다 -
다시 부르면 이어서 돈다. 끝 rc:
    0  바퀴가 끝났다 · summary.json
    3  크레딧이 끊겼다 - 그 세션은 세지 않고 상자를 되돌렸다. 충전 뒤 다시 부른다
    4  사람이 봐야 한다 - 설정이 RUN.json 과 다르다 · 카탈로그 설명이 바뀌었다 ·
       감사 결과를 읽지 못했다 · 상자가 없다
    5  멈춤 규칙 - 크레딧 창을 여섯 개 넘게 쓴다 (선언 「1단계 · 타당성」)

🔴 claude 는 쌍 내용에 관여하지 않는다 - 이 파일은 codex 를 부르고, 관문 · 재현 스크립트를
   권한 프로필 아래서 돌리고, 끝난 쌍을 복사만 한다. 프로필 · 환경 · 플래그는 xauthor.py 한 곳.
🔴 시도마다 새 세션이고 상자는 시도 사이에 남는다 - 다음 시도는 관문 출력만 받고
   앞 시도의 파일을 고친다. 크레딧으로 끊기거나 하네스가 중단한 세션은 세지 않고,
   그 세션 전의 상자로 되돌려 처음부터 다시 돈다.
🔴 안전 필터가 거절한 세션은 센다 - 그 쌍은 「refused」로 끝내고 그 분류도 닫는다.
   같은 분류의 새 쌍은 쌍 번호만 다른 같은 쓰기 요청을 보낸다 - 문구를 바꾸거나
   같은 요청을 되풀이해 필터를 넘기지 않는다 (수집 중 보정 2026-10-07 · DESIGN §7.10d).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codeproof_ai.corpus.decoy import TrapKind

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xauthor as xa
from agent_output import describe_codex, resolve_codex
from cross_family_prompt import build as audit_prompt

REPO = xa.REPO
PROMPT = REPO / "results" / "xauthor" / "author_prompt.md"
AUDIT_HEAD = REPO / "results" / "xauthor" / "audit_head.md"
AUDIT_SCHEMA = xa.AUDIT_SCHEMA
MODELS = REPO / "scripts" / "agent-models.json"
TEMPLATE = REPO / "corpus" / "decoys" / "_TEMPLATE"
VENV = xa.SHARED / "xauthor-venv-run"

PROMPT_SHA256 = "587e09bbd403f832cdffa6fad37d39a5799ba6ed335bdf8e6b6bd762ecfb66f1"
AUDIT_HEAD_SHA256 = "54a1372f654ce60038f3927604867f33aac1cb11be1195bd757cccfac25b249c"
"""수집 전에 커밋한 판 - 바꾸면 다른 실행이다 (선언 「쓰는 입력」). 테스트가 파일과 대조한다."""

KINDS = sorted(k.value for k in TrapKind)
ATTEMPTS = 3          # 쌍마다 시도 (선언 「시도 · 렌즈」)
FAILED_PER_KIND = 4   # 분류마다 버리는 쌍
MAX_WINDOWS = 6       # 1단계 크레딧 창 (선언 「1단계 · 타당성」)
GATE_TIMEOUT_S = 30 * 60
REPRO_TIMEOUT_S = 90  # 교차 패밀리 감사의 재현과 같다 (scripts/cross_family_repro.py)
CREDITS = "out of credits"
REFUSED = "content was flagged"
"""안전 필터의 거절 문구 [실측 · XC010 audit · 2026-10-07: "This content was flagged for possible
cybersecurity risk. …" · turn.failed · 0턴]."""
PAIR_FILES = ("meta.toml", "decoy.py", "twin.py", "proof.py", "mutants.py")
USAGE_KEYS = (
    "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
    "output_tokens", "reasoning_output_tokens",
)
CATEGORIES = ("write", "fix", "audit", "recheck")
SESSION_RECORD = re.compile(r"^(write-\d+|fix|audit|recheck)\.json$")
DONE, CUT, HUMAN, STOP = 0, 3, 4, 5


class Stop(Exception):  # noqa: N818 - 실패가 아니라 끝 rc 다
    def __init__(self, rc: int, why: str) -> None:
        super().__init__(why)
        self.rc = rc


class Refused(Exception):  # noqa: N818 - 실패가 아니라 그 쌍의 끝이다
    """안전 필터가 세션을 거절했다 - 그 쌍은 「refused」로 끝난다."""


@dataclass(frozen=True, slots=True)
class Session:
    rc: int
    timed_out: bool
    cut: bool
    turns: int
    usage: dict[str, int]
    refused: str | None = None
    """안전 필터의 거절 문구 - 없으면 None."""


@dataclass(frozen=True, slots=True)
class Pair:
    """쌍 하나 - 기록은 출력 디렉터리 아래, 상자와 스냅숏은 /Users/Shared 아래."""

    out: Path
    kind: str
    pid: str
    venv: Path

    @property
    def d(self) -> Path:
        return self.out / self.pid

    @property
    def box(self) -> Path:
        return xa.SHARED / f"xauthor-box-{self.pid}"

    @property
    def snap(self) -> Path:
        return xa.SHARED / f"xauthor-snap-{self.pid}"


# ── 판정 - 파일만 읽는다 ───────────────────────────────────────────────────────


def read_session(events: Path, err: Path, rc: int, *, timed_out: bool) -> Session:
    """세션 이벤트에서 쓴 양 · 크레딧 끊김 · 안전 필터 거절을 읽는다 - 끊김은 stderr 도 본다."""
    usage = dict.fromkeys(USAGE_KEYS, 0)
    turns, cut = 0, False
    refused: str | None = None
    text = events.read_text(encoding="utf-8", errors="replace") if events.exists() else ""
    for raw in text.split("\n"):
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "turn.completed":
            turns += 1
            got = ev.get("usage") if isinstance(ev.get("usage"), dict) else {}
            for k in USAGE_KEYS:
                usage[k] += int(got.get(k) or 0)
        elif ev.get("type") in ("error", "turn.failed"):
            said = json.dumps(ev, ensure_ascii=False)
            if CREDITS in said:
                cut = True
            elif REFUSED in said and refused is None:
                inner = ev.get("error")
                refused = str(ev.get("message") or (inner.get("message") if isinstance(inner, dict)
                                                     else None) or said)
    if err.exists() and CREDITS in err.read_text(encoding="utf-8", errors="replace"):
        cut = True
    return Session(rc, timed_out, cut, turns, usage, None if cut else refused)


def harness_problems(box: Path, pid: str, kind: str) -> tuple[Path | None, list[str]]:
    """관문 전에 하네스가 보는 것 - 쌍 폴더가 하나이고 분류가 맡긴 것인가."""
    found = sorted(
        p for p in (box / "corpus").iterdir() if p.is_dir() and p.name.startswith(f"{pid}-")
    )
    if len(found) != 1:
        names = [p.name for p in found] or "없음"
        want = f"하네스: corpus/ 에 {pid}-<짧은-설명> 폴더가 하나여야 한다"
        return None, [f"{want} - 찾은 것 {names}"]
    pair = found[0]
    try:
        meta = tomllib.loads((pair / "meta.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return pair, [f"하네스: meta.toml 을 읽지 못했다 - {exc}"]
    if meta.get("trap_kind") != kind:
        return pair, [f"하네스: trap_kind 는 {kind} 여야 한다 - 적힌 것 {meta.get('trap_kind')!r}"]
    return pair, []


def reproduced(stdout: str) -> bool:
    """감사 머리말의 약속 - 마지막 줄이 정확히 REPRODUCED 일 때만 (NOT REPRODUCED 는 아니다)."""
    lines = [ln.strip() for ln in stdout.split("\n") if ln.strip()]
    return bool(lines) and lines[-1] == "REPRODUCED"


def findings_of(last: Path) -> list[dict[str, str]] | None:
    """감사의 마지막 답 - 스키마 모양이 아니면 None (판정하지 않고 사람이 본다)."""
    try:
        data = json.loads(last.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    items = data.get("findings") if isinstance(data, dict) else None
    keys = ("kind", "lines", "summary", "evidence", "repro")
    if not isinstance(items, list) or not all(
        isinstance(f, dict) and all(isinstance(f.get(k), str) for k in keys) for f in items
    ):
        return None
    return [{k: f[k] for k in keys} for f in items]


def events_of(out: Path) -> list[dict[str, Any]]:
    path = out / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").split("\n") if ln]


def windows_used(out: Path) -> int:
    """지금까지 쓴 크레딧 창 - 끊길 때마다 창 하나가 끝난다 (하네스 중단은 세지 않는다).

    충전 전의 재시도가 끊긴 것(`credit_cut_idle`)은 세지 않는다 - 그 창은 앞의 끊김에서 이미 끝났다.
    """
    return 1 + sum(e.get("event") == "credit_cut" for e in events_of(out))


def window_has_sessions(out: Path) -> bool:
    """지금 창에서 끝난 세션이 있는가 - 없이 끊겼으면 충전 전의 재시도다."""
    now = windows_used(out)
    return any(
        _load(q).get("window") == now
        for d in pair_dirs(out) for q in d.iterdir() if SESSION_RECORD.match(q.name)
    )


def over_budget(out: Path) -> bool:
    """1단계 멈춤 규칙 - 크레딧 창 여섯 개를 **넘게** 쓰면 멈춘다 (여섯 번째 창은 쓴다)."""
    return windows_used(out) > MAX_WINDOWS


def pair_dirs(out: Path) -> list[Path]:
    return sorted(p for p in out.iterdir() if p.is_dir() and re.fullmatch(r"XC\d{3}", p.name))


def pair_kind(d: Path) -> str:
    return str(json.loads((d / "pair.json").read_text(encoding="utf-8"))["kind"])


def outcome_of(d: Path) -> str | None:
    path = d / "outcome.json"
    return str(json.loads(path.read_text(encoding="utf-8"))["outcome"]) if path.exists() else None


# ── 프롬프트 ──────────────────────────────────────────────────────────────────


def _task_head(pid: str, kind: str) -> str:
    return (
        f"- 쌍 식별자: `{pid}` — 쌍 폴더는 `corpus/{pid}-<짧은-설명>/` 하나다.\n"
        f"- 분류(`trap_kind`): `{kind}`\n"
    )


def task_write(pid: str, kind: str, attempt: int, gate_out: str | None) -> str:
    if attempt == 1 or gate_out is None:
        return (
            f"## 이번 과제\n\n{_task_head(pid, kind)}\n"
            "이 분류의 쌍 하나를 처음부터 끝까지 쓰고 관문을 넘긴다.\n"
        )
    return (
        f"## 이번 과제 — 시도 {attempt}/{ATTEMPTS}\n\n{_task_head(pid, kind)}\n"
        "앞 시도에서 쓴 파일이 상자에 그대로 있다. "
        "하네스가 돌린 관문이 아래처럼 실패했다 — 고쳐서 관문을 넘긴다.\n\n"
        f"```text\n{gate_out.rstrip()}\n```\n"
    )


def task_fix(pid: str, kind: str, problems: list[dict[str, Any]]) -> str:
    parts = [
        f"## 이번 과제 — 감사가 재현한 문제\n\n{_task_head(pid, kind)}\n"
        "이 쌍은 관문을 넘었다. 다른 문맥의 감사가 아래 문제를 냈고, "
        "하네스가 재현 스크립트를 같은 권한 아래서 돌려 재현됐다.\n"
        "이 세션 안에 문제마다 하나를 한다 — "
        "고친다 · 주장을 좁힌다 · 위협 모델 밖이라는 이유를 적는다. "
        "이유는 상자 맨 위 `response.md` 에 문제 번호와 함께 적는다.\n"
        "끝나면 하네스가 관문을 다시 돌리고 같은 감사로 한 번 더 본다 — "
        "그때도 재현되는 문제가 남으면 이 쌍은 버린다.\n"
    ]
    for n, p in enumerate(problems, 1):
        parts.append(
            f"### 문제 {n} — `{p['kind']}` · decoy.py {p['lines']}\n\n{p['summary']}\n\n"
            f"근거: {p['evidence']}\n\n"
            f"재현 스크립트:\n\n```python\n{p['repro'].rstrip()}\n```\n\n"
            f"재현 출력 (끝 20줄):\n\n```text\n{p['stdout_tail'].rstrip()}\n```\n"
        )
    return "\n".join(parts)


def author(task: str) -> str:
    return PROMPT.read_text(encoding="utf-8").rstrip() + "\n\n" + task


# ── 실행 ──────────────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _event(out: Path, event: str, **fields: object) -> None:
    with (out / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": _now(), "event": event, **fields}, ensure_ascii=False) + "\n")


def _tail(text: str, n: int = 20) -> str:
    return "\n".join(text.rstrip().split("\n")[-n:])


def run_group(
    cmd: list[str], *, env: dict[str, str], timeout: float,
    stdout: Any = subprocess.PIPE, stderr: Any = subprocess.PIPE,
) -> tuple[int, bool, str, str]:
    """프로세스 그룹으로 띄운다 - 시간이 넘거나 하네스가 멈추면 손자 프로세스까지 끝낸다."""
    proc = subprocess.Popen(  # noqa: S603 - 인자는 이 파일과 xauthor.py 가 만든다
        cmd, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, env=env,
        text=True, start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
        return -signal.SIGKILL, True, out or "", err or ""
    except BaseException:
        os.killpg(proc.pid, signal.SIGKILL)
        raise
    return proc.returncode, False, out or "", err or ""


def _sandboxed(workdir: Path, venv: Path, *cmd: str) -> list[str]:
    """모델이 쓴 코드를 돌리는 자리 - 저자 셸과 같은 프로필 (선언 「상자」 행 · 수집 전 수정 ④)."""
    return [
        str(xa.CODEX), "sandbox", "-c", f"permissions.box.filesystem={xa.profile(venv)}",
        "-P", "box", "-C", str(workdir), "--", *cmd,
    ]


def snapshot(box: Path, snap: Path) -> None:
    tmp = snap.with_name(snap.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(box, tmp, symlinks=True)
    shutil.rmtree(snap, ignore_errors=True)
    tmp.rename(snap)


def abandon(d: Path, step: str, why: str, box: Path, snap: Path | None) -> None:
    """끊긴 세션을 세지 않는다 - 기록은 cut/ 로 옮기고 상자를 그 세션 전으로 되돌린다."""
    cut = d / "cut"
    cut.mkdir(exist_ok=True)
    n = len({p.name.split("-", 1)[0] for p in cut.iterdir()}) + 1
    for p in sorted(d.glob(f"{step}.*")):
        p.rename(cut / f"{n:02d}-{p.name}")
    (cut / f"{n:02d}-{step}.reason").write_text(why + "\n", encoding="utf-8")
    if snap is not None:
        shutil.rmtree(box, ignore_errors=True)
        shutil.copytree(snap, box, symlinks=True)


def session(
    p: Pair, step: str, prompt: str, *, box: Path, snap: Path | None, schema: Path | None = None,
) -> None:
    """codex 세션 한 번 - 끝났으면 건너뛰고, 하네스가 중단한 흔적이 있으면 세지 않고 다시 돈다."""
    d = p.d
    if (d / f"{step}.json").exists():
        # 끝난 세션이 거절이면 같은 요청을 다시 보내지 않는다 - 거절을 알기 전의 기록도 읽는다
        done = read_session(d / f"{step}.jsonl", d / f"{step}.err", 0, timed_out=False)
        if done.refused:
            _refused(p, step, done.refused)
        return
    if (d / f"{step}.jsonl").exists():
        abandon(d, step, "interrupted", box, snap)
        _event(p.out, "interrupted", pair=p.pid, step=step)
    if snap is not None:
        snapshot(box, snap)
    (d / f"{step}.prompt.txt").write_text(prompt, encoding="utf-8")
    args = xa.exec_args(box, p.venv, prompt, d / f"{step}.last.txt", ephemeral=True, schema=schema)
    started = time.time()
    with (d / f"{step}.jsonl").open("w", encoding="utf-8") as ev, \
            (d / f"{step}.err").open("w", encoding="utf-8") as er:
        rc, timed_out, _, _ = run_group(
            args, env=xa.environment(box, p.venv), timeout=xa.EXEC_TIMEOUT_S, stdout=ev, stderr=er,
        )
    s = read_session(d / f"{step}.jsonl", d / f"{step}.err", rc, timed_out=timed_out)
    if s.cut:
        # 🔴 끝난 세션 없이 끊긴 것은 창을 끝내지 않는다 - 구동기는 충전 전에도 다시 부른다
        idle = not window_has_sessions(p.out)
        abandon(d, step, "credits", box, snap)
        _event(p.out, "credit_cut_idle" if idle else "credit_cut", pair=p.pid, step=step)
        raise Stop(CUT, f"{p.pid} {step} 에서 크레딧이 끊겼다 - 세지 않고 되돌렸다")
    _json(d / f"{step}.json", {
        "step": step, "category": "write" if step.startswith("write-") else step,
        "rc": rc, "timed_out": timed_out, "turns": s.turns, "usage": s.usage,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
        "seconds": round(time.time() - started), "window": windows_used(p.out),
        "refused": s.refused,
    })
    if s.refused:
        _refused(p, step, s.refused)


def _refused(p: Pair, step: str, said: str) -> None:
    """🔴 거절은 1급 기록이다 - 이벤트로 한 번 남기고 그 쌍을 끝낸다 (되풀이하지 않는다)."""
    seen = any(
        e.get("event") == "refused" and e.get("pair") == p.pid and e.get("step") == step
        for e in events_of(p.out)
    )
    if not seen:
        _event(p.out, "refused", pair=p.pid, step=step, message=said)
    raise Refused(f"{p.pid} {step} 를 안전 필터가 거절했다 - {said}")


def gate(p: Pair, step: str) -> bool:
    """관문 - 하네스 확인과 `codeproof decoy gate` 를 권한 프로필 아래서. 출력은 그대로 남긴다."""
    record = p.d / f"{step}.json"
    if not record.exists():
        pair, problems = harness_problems(p.box, p.pid, p.kind)
        rc: int | None = None
        text = ""
        if pair is not None:
            codeproof = str(p.venv / "bin" / "codeproof")
            cmd = _sandboxed(p.box, p.venv, codeproof, "decoy", "gate", p.pid, "--corpus", "corpus")
            rc, timed_out, stdout, stderr = run_group(
                cmd, env=xa.environment(p.box, p.venv), timeout=GATE_TIMEOUT_S,
            )
            text = stdout + stderr
            if timed_out:
                problems.append(f"하네스: 관문이 {GATE_TIMEOUT_S // 60}분 안에 끝나지 않았다")
        body = "\n".join([*problems, text]).strip() + "\n"
        (p.d / f"{step}.txt").write_text(body, encoding="utf-8")
        _json(record, {"pass": not problems and rc == 0, "rc": rc, "problems": problems})
    return bool(_load(record)["pass"])


def repro_one(pair: Path, finding: dict[str, str], venv: Path) -> dict[str, Any]:
    """재현 스크립트를 상자 밖의 새 디렉터리에서 같은 프로필로 - decoy.py 와 스크립트만 둔다."""
    rdir = Path(tempfile.mkdtemp(prefix="xauthor-repro-", dir=xa.SHARED))
    try:
        for sub in ("tmp", "home"):
            (rdir / sub).mkdir()
        shutil.copy2(pair / "decoy.py", rdir / "decoy.py")
        (rdir / "repro.py").write_text(finding["repro"], encoding="utf-8")
        cmd = _sandboxed(rdir, venv, str(venv / "bin" / "python"), "-E", "-s", "repro.py")
        rc, timed_out, stdout, stderr = run_group(
            cmd, env=xa.environment(rdir, venv), timeout=REPRO_TIMEOUT_S,
        )
    finally:
        shutil.rmtree(rdir, ignore_errors=True)
    return {
        **finding, "reproduced": reproduced(stdout) and not timed_out, "rc": rc,
        "timed_out": timed_out, "stdout_tail": _tail(stdout), "stderr_tail": _tail(stderr),
    }


def audit(p: Pair, step: str) -> list[dict[str, Any]]:
    """다른 문맥의 codex 감사 한 번과 재현 - 재현된 지적만 돌려준다."""
    rep = p.d / f"{step}.repro.json"
    if not rep.exists():
        pair, problems = harness_problems(p.box, p.pid, p.kind)
        if pair is None or problems:
            raise Stop(HUMAN, f"{p.pid} {step} 앞에서 쌍 폴더를 찾지 못했다: {problems}")
        abox = Path(tempfile.mkdtemp(prefix="xauthor-audit-", dir=xa.SHARED))
        try:
            for sub in ("tmp", "home"):
                (abox / sub).mkdir()
            prompt = audit_prompt(pair, AUDIT_HEAD.read_text(encoding="utf-8").rstrip())
            session(p, step, prompt, box=abox, snap=None, schema=AUDIT_SCHEMA)
        finally:
            shutil.rmtree(abox, ignore_errors=True)
        last = p.d / f"{step}.last.txt"
        found = findings_of(last)
        if found is None:
            raise Stop(HUMAN, f"{p.pid} {step} 결과를 스키마 모양으로 읽지 못했다 - {last}")
        _json(rep, [repro_one(pair, f, p.venv) for f in found])
    return [f for f in _load(rep) if f["reproduced"]]


def finish(p: Pair, outcome: str, why: str) -> None:
    """쌍 파일만 복사한다 - 상자의 home · tmp 는 기록이 아니다. 끝난 쌍의 상자와 스냅숏은 지운다."""
    corpus = p.box / "corpus"
    pair = next((q for q in sorted(corpus.iterdir()) if q.name.startswith(f"{p.pid}-")), None)
    extras: list[str] = []
    if pair is not None:
        dest = p.d / "final" / pair.name
        dest.mkdir(parents=True, exist_ok=True)
        for name in PAIR_FILES:
            if (pair / name).exists():
                shutil.copy2(pair / name, dest / name)
        extras = sorted(q.name for q in pair.iterdir() if q.name not in PAIR_FILES)
    if (p.box / "response.md").exists():
        shutil.copy2(p.box / "response.md", p.d / "response.md")
    _json(p.d / "outcome.json", {
        "pair": p.pid, "outcome": outcome, "why": why,
        "pair_dir": pair.name if pair else None, "extras": extras,
    })
    shutil.rmtree(p.box, ignore_errors=True)
    shutil.rmtree(p.snap, ignore_errors=True)


def make_box(box: Path) -> None:
    """저자 상자 - 빈 코퍼스 폴더 · `_TEMPLATE` · 고정 문서 (선언 「상자」 행)."""
    for sub in ("tmp", "home", "corpus"):
        (box / sub).mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(TEMPLATE, box / "corpus" / "_TEMPLATE", ignore=ignore)
    shutil.copy2(PROMPT, box / "author_prompt.md")


def run_pair(p: Pair) -> None:
    """쌍 하나 - 안전 필터가 어느 세션이든 거절하면 그 쌍은 「refused」로 끝난다."""
    try:
        _run_pair(p)
    except Refused as r:
        finish(p, "refused", str(r))


def _run_pair(p: Pair) -> None:
    """쓰기 (시도 3번 · 시도마다 관문) → 감사 → 고침 → 관문 → 재확인 (선언 「시도 · 렌즈」)."""
    if not p.box.exists():
        if any(p.d.glob("write-*")):
            raise Stop(HUMAN, f"{p.pid} 의 상자가 없다 - {p.box}")
        make_box(p.box)
    passed = False
    for a in range(1, ATTEMPTS + 1):
        if not (p.d / f"gate-{a}.json").exists():
            gate_out = (p.d / f"gate-{a - 1}.txt").read_text(encoding="utf-8") if a > 1 else None
            prompt = author(task_write(p.pid, p.kind, a, gate_out))
            session(p, f"write-{a}", prompt, box=p.box, snap=p.snap)
        if gate(p, f"gate-{a}"):
            passed = True
            break
    if not passed:
        finish(p, "failed", f"관문 {ATTEMPTS}번 실패")
        return
    problems = audit(p, "audit")
    if not problems:
        finish(p, "accepted", "감사에서 재현된 문제가 없다")
        return
    session(p, "fix", author(task_fix(p.pid, p.kind, problems)), box=p.box, snap=p.snap)
    if not gate(p, "gate-fix"):
        finish(p, "failed", "고친 뒤 관문을 넘지 못했다")
    elif audit(p, "recheck"):
        finish(p, "failed", "재확인에서 재현되는 문제가 남았다")
    else:
        finish(p, "accepted", "재확인에서 재현된 문제가 없다")


# ── 준비 · 기록 ────────────────────────────────────────────────────────────────

SIGNED = (
    "codex", "model", "effort", "author_prompt_sha256", "audit_head_sha256",
    "audit_schema_sha256", "profile",
)
"""실행을 가르는 항목 - 이어 돌 때 하나라도 다르면 멈춘다 (A2b 와 같은 원칙)."""


def signed_fields() -> dict[str, str]:
    return {
        "codex": xa.CODEX_VERSION, "model": xa.MODEL, "effort": xa.EFFORT,
        "author_prompt_sha256": _sha256(PROMPT), "audit_head_sha256": _sha256(AUDIT_HEAD),
        "audit_schema_sha256": _sha256(AUDIT_SCHEMA), "profile": xa.profile(Path("<venv>")),
    }


def check_catalog() -> str:
    """카탈로그 설명이 받아들인 모델의 것과 같은가 (선언 「저자」 행 - 바퀴마다)."""
    done = subprocess.run(  # noqa: S603 - 고정 경로의 codex
        [str(xa.CODEX), "debug", "models"],
        capture_output=True, text=True, timeout=120, check=False,
    )
    try:
        catalog = json.loads(done.stdout)
        resolve_codex(catalog, xa.EFFORT, xa.MODEL)
    except Exception as exc:  # 카탈로그를 못 읽거나 모델 · effort 가 없다 - 사람이 본다
        why = f"카탈로그에서 {xa.MODEL} (effort {xa.EFFORT}) 를 확인하지 못했다: {exc}"
        raise Stop(HUMAN, why) from exc
    note = describe_codex(catalog, xa.MODEL)
    want = json.loads(MODELS.read_text(encoding="utf-8"))["codex"]["note"]
    if note != want:
        raise Stop(HUMAN, f"카탈로그 설명이 바뀌었다: {note!r} (받아들인 것 {want!r})")
    return note


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603
        [xa._tool("git"), *args], cwd=REPO, capture_output=True, text=True, check=False,
    ).stdout.strip()


def _first_start() -> dict[str, str]:
    """첫 시작 - 커밋한 하네스로 venv 를 만들고, 격리를 다시 점검하고, 카탈로그를 대조한다."""
    paths = ("src", "scripts", "results/xauthor", str(TEMPLATE))
    if dirty := _git("status", "--porcelain", "--", *paths):
        why = "하네스가 커밋되지 않았다 - venv 와 프롬프트는 커밋과 같아야 한다"
        raise Stop(HUMAN, f"{why}:\n{dirty}")
    if xa.check() != 0:  # 모델 없이 - 선언의 격리가 오늘 이 기계에서 성립하는가
        raise Stop(HUMAN, "격리 점검이 기대와 다르다 - scripts/xauthor.py check")
    with tempfile.TemporaryDirectory() as build:
        wheel = xa.build_wheel(Path(build))
        shutil.rmtree(VENV, ignore_errors=True)
        python = str(VENV / "bin" / "python")
        for cmd in (
            [str(xa.PYTHON), "-m", "venv", str(VENV)],
            [xa._tool("uv"), "pip", "install", "--quiet", "--python", python, str(wheel)],
        ):
            if (done := xa._run(cmd)).returncode:
                raise Stop(HUMAN, f"venv 를 만들지 못했다: {done.stderr}")
        wheel_sha = _sha256(wheel)
    return {"wheel_sha256": wheel_sha, "model_note": check_catalog()}


def preflight(out: Path) -> Path:
    """판 · 고정 문서 · RUN.json · venv · 카탈로그 - 하나라도 어긋나면 시작하지 않는다."""
    if (found := xa._codex_version()) != xa.CODEX_VERSION:
        raise Stop(HUMAN, f"codex 판이 다르다: {found!r} (선언 {xa.CODEX_VERSION})")
    if (_sha256(PROMPT), _sha256(AUDIT_HEAD)) != (PROMPT_SHA256, AUDIT_HEAD_SHA256):
        raise Stop(HUMAN, "고정 문서가 커밋한 판과 다르다 - author_prompt.md · audit_head.md")
    run_json = out / "RUN.json"
    fields = signed_fields()
    if run_json.exists():
        rec = _load(run_json)
        if diffs := [k for k in SIGNED if rec.get(k) != fields[k]]:
            raise Stop(HUMAN, f"RUN.json 의 설정과 다르다: {diffs}")
        if not (VENV / "bin" / "codeproof").exists():
            raise Stop(HUMAN, f"venv 가 없다 - {VENV} (다시 만들면 다른 하네스일 수 있다)")
    else:
        first = _first_start()
        rec = {
            "what": "DESIGN §7.10d 1단계 - codex 가 쓴 쌍 (분류 이름순으로 한 쌍씩)",
            **fields, **first, "commit": _git("rev-parse", "HEAD"),
            "rounds": {"1": {"started": _now(), "model_note": first["model_note"]}},
            "caps": {
                "attempts": ATTEMPTS, "failed_pairs_per_kind": FAILED_PER_KIND,
                "max_windows": MAX_WINDOWS, "session_s": xa.EXEC_TIMEOUT_S,
            },
            "invocations": [],
        }
    rec["invocations"].append({
        "at": _now(), "commit": _git("rev-parse", "HEAD"),
        "runner_sha256": _sha256(Path(__file__)),
    })
    _json(run_json, rec)
    return VENV


def summarize(out: Path) -> dict[str, Any]:
    """1단계가 내는 것 - 채운 분류 수 · 호출과 입력 토큰(캐시 따로) · 크레딧 창.

    실패한 시도까지 센다 (선언 「1단계 · 타당성」).
    """
    zero = {"sessions": 0, "turns": 0, **dict.fromkeys(USAGE_KEYS, 0)}
    totals = {c: dict(zero) for c in CATEGORIES}
    rows = []
    for d in pair_dirs(out):
        records = [_load(q) for q in sorted(d.iterdir()) if SESSION_RECORD.match(q.name)]
        for r in records:
            t = totals[r["category"]]
            t["sessions"] += 1
            t["turns"] += r["turns"]
            for k in USAGE_KEYS:
                t[k] += r["usage"][k]
        cut = d / "cut"
        reasons = sorted(cut.glob("*.reason")) if cut.exists() else []
        rows.append({
            "pair": d.name, "kind": pair_kind(d), "outcome": outcome_of(d) or "진행 중",
            "attempts": sum(r["category"] == "write" for r in records), "sessions": len(records),
            "not_counted": [q.read_text(encoding="utf-8").strip() for q in reasons],
        })
    filled = sorted({r["kind"] for r in rows if r["outcome"] == "accepted"})
    events = events_of(out)
    return {
        "kinds_filled": len(filled), "kinds": filled, "windows_used": windows_used(out),
        "credit_cuts": sum(e.get("event") == "credit_cut" for e in events),
        "idle_cuts": sum(e.get("event") == "credit_cut_idle" for e in events),
        "refused": sum(e.get("event") == "refused" for e in events),
        "interrupted": sum(e.get("event") == "interrupted" for e in events),
        "totals": totals, "pairs": rows,
    }


def kind_done(outcomes: list[str | None]) -> bool:
    """분류 하나가 끝났는가 - 받아들인 쌍이 있거나, 거절된 쌍이 있거나, 실패한 쌍이 한도에 닿았다.

    🔴 거절 하나로 닫는다 - 새 쌍의 첫 쓰기는 쌍 번호만 다른 같은 요청이고, 필터를 넘긴 쌍만
       남기면 그 분류가 필터로 골라진다.
    """
    refused = "refused" in outcomes
    return "accepted" in outcomes or refused or outcomes.count("failed") >= FAILED_PER_KIND


def run(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / ".lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("rc=4 · 이 출력 디렉터리에서 다른 실행기가 돌고 있다", file=sys.stderr)
        return HUMAN
    try:
        venv = preflight(out)
        if over_budget(out):
            why = f"크레딧 창 {MAX_WINDOWS}개를 넘게 쓴다 ({windows_used(out)}번째 창)"
            raise Stop(STOP, why)
        _event(out, "start", window=windows_used(out))
        for kind in KINDS:
            while True:
                mine = [d for d in pair_dirs(out) if pair_kind(d) == kind]
                outcomes = [outcome_of(d) for d in mine]
                if kind_done(outcomes):
                    break
                d = next((m for m, o in zip(mine, outcomes, strict=True) if o is None), None)
                if d is None:
                    d = out / f"XC{len(pair_dirs(out)) + 1:03d}"
                    d.mkdir()
                    _json(d / "pair.json", {"kind": kind, "round": 1, "created": _now()})
                run_pair(Pair(out=out, kind=kind, pid=d.name, venv=venv))
    except Stop as stop:
        _event(out, "stop", rc=stop.rc, why=str(stop))
        print(f"rc={stop.rc} · {stop}", file=sys.stderr)
        return stop.rc
    summary = summarize(out)
    _json(out / "summary.json", summary)
    print(f"채운 분류 {summary['kinds_filled']}/{len(KINDS)} · 크레딧 창 {summary['windows_used']}")
    return DONE


def main(argv: list[str]) -> int:
    match argv:
        case [out, "--summary"]:
            print(json.dumps(summarize(Path(out).resolve()), ensure_ascii=False, indent=2))
            return DONE
        case [out]:
            # 구동기가 멈추면 SIGTERM 이 온다 - 예외로 바꿔 run_group 이 codex 그룹까지 끝내게 한다
            signal.signal(signal.SIGTERM, lambda *_: sys.exit(128 + signal.SIGTERM))
            return run(Path(out).resolve())
        case _:
            print(__doc__, file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
