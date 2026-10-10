"""측정 뒤 claude 감사 - DESIGN §7.10d 「측정 뒤 claude 감사」.

    uv run python scripts/claude_audit.py <출력>             🔴 구독 사용량 - 측정이 끝난 뒤
    uv run python scripts/claude_audit.py <출력> --canary    🔴 구독 사용량 - 목표 150쌍의 D115
    uv run python scripts/claude_audit.py <출력> --summary   지금까지의 요약 (모델 없이)

쌍마다 감사 → 재현 → 판정 A · B 를 돈다. 출력 디렉터리의 파일이 상태다 - 다시 부르면 이어서 돈다.
끝 rc:
    0  다 돌았다 · 판정자마다 라벨 문제 목록 (`results/xauthor/label-issues/`) · summary.json
    4  사람이 봐야 한다 - 측정 전이다 · 설정이 RUN.json 과 다르다 · 고정 문서가 커밋한 판과
       다르다 · 답을 읽지 못했다 (그 세션은 cut/ 로 옮기고 세지 않는다)

🔴 감사 · 재현은 codex 감사와 같은 부품이다 - 머리말 · 스키마 · 프롬프트 생성기 · 재현 함수 ·
   권한 프로필. 다른 것은 부르는 CLI 하나다.
🔴 판정자는 감사와 같이 도구가 없는 빈 디렉터리에서 돈다 - 측정값을 볼 길이 구조로 없다.
🔴 고치지 않는다 · 채점에 쓰지 않는다 - 쓰는 곳은 출력 디렉터리와 라벨 문제 목록뿐이다.
"""

from __future__ import annotations

import fcntl
import getpass
import hashlib
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from codeproof_ai.cli import _xauthor_measured
from codeproof_ai.corpus.decoy import pair_dirs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xauthor as xa
import xauthor_run as xr
from agent_output import _models_in, pinned_problem
from cross_family_prompt import build as audit_prompt

if TYPE_CHECKING:
    from collections.abc import Callable

REPO = xr.REPO
JUDGE_HEAD = REPO / "results" / "xauthor" / "judge_head.md"
JUDGE_SCHEMA = REPO / "results" / "xauthor" / "judge_schema.json"
JUDGE_HEAD_SHA256 = "39878ddfc4d5245998eebff95cb03453e8a0124157a6cba67836d35eaddbc06d"
"""측정 전에 커밋한 판 - 바꾸면 다른 실행이다. 테스트가 파일과 대조한다."""
MODELS = xr.MODELS
CORPUS = REPO / "corpus" / "xauthor" / "codex"
AGENTS = REPO / "results" / "xauthor" / "agent"
REFERENCE = (REPO / "corpus" / "decoys", REPO / "results" / "agent")
"""견줄 측정 (목표 150쌍) - `xauthor-report` 의 기본값과 같다."""
ISSUES = REPO / "results" / "xauthor" / "label-issues"
CANARY = REPO / "corpus" / "decoys"
CANARY_PAIR = "D115"
"""관문 기준 쌍 (xauthor.GATE_PAIR) - claude 가 쓴 쌍이라 측정 전에 봐도 된다."""
VENV = xr.VENV
"""재현을 돌리는 venv - codex 감사의 재현과 같은 것이다."""
CLAUDE = Path("/Users/Shared/xauthor-tools/claude-code-2.1.284/node_modules/.bin/claude")
CLAUDE_VERSION = "2.1.284 (Claude Code)"
"""측정과 같은 판 (선언 「측정」) - 격리 설치라 자동 업데이트로 바뀌지 않는다 (xa.CODEX 와 같다)."""
EFFORT = "high"  # codex 감사와 같다 (선언 「시도 · 렌즈」)
JUDGES = ("A", "B")
VERDICTS = ("IN", "OUT", "VACUOUS", "NOT_REPRODUCED")
"""교차 패밀리 감사 판정의 어휘 (results/cross-family-audit/verdicts.jsonl)."""
TIMEOUT_S = 900  # 교차 패밀리 감사와 같다 (scripts/cross-family-audit.sh)
FLAGS = (
    "--safe-mode", "--strict-mcp-config", "--no-session-persistence",
    "--permission-mode", "dontAsk", "--tools", "", "--output-format", "json",
)
"""리뷰 실행기와 같은 격리 (review-with-agent.sh) - 도구만 없다. 코드는 프롬프트에 있다."""
SWITCHES = {
    "DISABLE_AUTOUPDATER": "1",
    "CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1",
    "CLAUDE_CODE_DISABLE_REFUSAL_RETRY": "1",
}
"""CLI 의 동작을 바꾸는 환경 변수. 🔴 거절을 감추는 두 길을 끈다 [소스: 2.1.284 바이너리 문자열] -
거절 대체(`hL()` - 거절된 턴을 다른 모델로 다시 돈다)와 같은 모델 재시도(`qi()` - 한 번 더
이어 돈다). 켜 두면 거절이 1급 기록으로 남지 않고 필터를 넘긴 답이 실린다."""
SIGNED = (
    "cli", "model", "effort", "flags", "env", "audit_head_sha256", "audit_schema_sha256",
    "judge_head_sha256", "judge_schema_sha256", "prompt_builder_sha256", "profile",
)
"""실행을 가르는 항목 - 이어 돌 때 하나라도 다르면 멈춘다 (A2b 와 같은 원칙)."""
Stop = xr.Stop
DONE, HUMAN = xr.DONE, xr.HUMAN


def environment() -> dict[str, str]:
    """최소 환경 - 띄운 세션의 변수(CLAUDECODE · CLAUDE_CODE_*)를 물려주지 않는다.

    CLI 는 CLAUDE_CODE_EFFORT_LEVEL 을 effort 로 읽는다 [소스: 2.1.284 바이너리 문자열] ·
    [실측 2026-10-09] Claude Code 세션의 셸에는 부모 세션의 메시징 소켓 · 자식 세션 표시가 있다.
    이 환경에서도 로그인은 그대로다 [실측] - `claude auth status` 가 loggedIn.
    """
    user = getpass.getuser()
    return {
        "PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "USER": user, "LOGNAME": user,
        "LANG": "en_US.UTF-8", "TMPDIR": tempfile.gettempdir(), **SWITCHES,
    }


def claude_args(prompt: str, schema: Path, model: str) -> list[str]:
    schema_text = schema.read_text(encoding="utf-8")
    return [
        str(CLAUDE), "-p", prompt, "--model", model, "--effort", EFFORT, *FLAGS,
        "--json-schema", schema_text,
    ]


def accepted_model() -> str:
    """받아들인 claude 모델 (scripts/agent-models.json) - 측정의 claude 리뷰어와 같다."""
    return str(xr._load(MODELS)["claude"]["model"])


def measured_model(
    corpus: Path, agents: Path, reference: tuple[Path, Path] = REFERENCE
) -> str | None:
    """측정이 끝났으면 claude 묶음의 모델 - `xauthor-report` 가 받아들일 측정일 때만. 아니면 None.

    🔴 보고서와 같은 판정 하나를 쓴다 (`_xauthor_measured` - 묶음 수 · 3회 · 손잡이 · 쌍 전부 ·
       설정). 라벨 문제 목록은 이 감사가 만드는 것이라 비워서 묻는다.
    """
    got = _xauthor_measured(corpus, agents, reference, {})
    return None if got is None else dict(got[0][0].setup).get("model")


def answer(envelope: object, model: str, key: str) -> dict[str, Any]:
    """봉투에서 스키마 모양의 답 - 오류 · 다른 모델 · 스키마 밖이면 ValueError.

    [실측 · 리뷰 실행 1860건] 스키마를 준 호출은 전부 `structured_output` 으로 답했다 -
    본문에서 답을 찾지 않는다.
    """
    if not isinstance(envelope, dict):
        raise ValueError("봉투가 객체가 아니다")
    if envelope.get("is_error"):
        detail = f"{envelope.get('subtype')} {str(envelope.get('result'))[:200]}"
        raise ValueError(f"is_error: {detail}")
    if reason := pinned_problem(envelope, model):
        raise ValueError(reason)
    out = envelope.get("structured_output")
    if not (isinstance(out, dict) and isinstance(out.get(key), list)):
        raise ValueError(f"스키마 모양의 답({key})이 없다")
    return out


def verdicts_of(last: Path, count: int) -> list[dict[str, Any]] | None:
    """판정자의 답 - 지적 1~count 를 한 번씩 판정하지 않았으면 None (사람이 본다)."""
    try:
        items = json.loads(last.read_text(encoding="utf-8")).get("verdicts")
    except (OSError, ValueError, AttributeError):
        return None
    keys = ("finding", "verdict", "basis")
    if not isinstance(items, list) or not all(
        isinstance(v, dict) and type(v.get("finding")) is int
        and v.get("verdict") in VERDICTS and isinstance(v.get("basis"), str)
        for v in items
    ):
        return None
    if sorted(v["finding"] for v in items) != list(range(1, count + 1)):
        return None
    return sorted(({k: v[k] for k in keys} for v in items), key=lambda v: v["finding"])


def session(
    d: Path, step: str, prompt: str, *, schema: Path, key: str, model: str,
    check: Callable[[Path], list[dict[str, Any]] | None],
) -> dict[str, Any]:
    """claude 한 번 - 끝난 세션은 다시 부르지 않는다. 읽지 못한 답은 세지 않고 사람에게 넘긴다.

    🔴 거절(`stop_reason: refusal`)은 1급 기록이다 (D5) - 끝난 세션으로 남기고 다시 묻지 않는다.
    🔴 하네스가 끊겨 남은 흔적(봉투 · stderr)은 덮지 않고 cut/ 으로 옮긴다 - 원본을 전부 남기고,
       요약이 그 호출도 센다 (xauthor_run.session 과 같다).
    """
    record = d / f"{step}.json"
    if record.exists():
        return dict(xr._load(record))
    raw, err, last = (d / f"{step}{s}" for s in (".claude.json", ".err", ".last.json"))
    if raw.exists():
        xr.abandon(d, step, "interrupted", Path(), None)
    (d / f"{step}.prompt.md").write_text(prompt, encoding="utf-8")
    box = Path(tempfile.mkdtemp(prefix="claude-audit-"))
    started = time.time()
    try:
        with raw.open("w", encoding="utf-8") as so, err.open("w", encoding="utf-8") as se:
            rc, timed_out, _, _ = xr.run_group(
                claude_args(prompt, schema, model), env=environment(), timeout=TIMEOUT_S,
                stdout=so, stderr=se, cwd=box,
            )
        left = sorted(p.name for p in box.iterdir())
    finally:
        shutil.rmtree(box, ignore_errors=True)
    try:
        envelope = json.loads(raw.read_text(encoding="utf-8"))
        refused = isinstance(envelope, dict) and envelope.get("stop_reason") == "refusal"
        found: list[dict[str, Any]] | None = []
        if not refused:
            xr._json(last, answer(envelope, model, key))
            found = check(last)
    except ValueError as exc:
        found, why = None, str(exc)
    else:
        why = "스키마 모양으로 읽지 못했다"
    if timed_out or found is None:
        xr.abandon(d, step, "timeout" if timed_out else why, Path(), None)
        raise Stop(HUMAN, f"{d.name} {step} - {'시간 초과' if timed_out else why} (cut/ 로 옮겼다)")
    rec = {
        "step": step, "rc": rc, "refused": refused, "answer": found,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "usage": envelope.get("usage"), "model_usage": sorted(_models_in(envelope)),
        "turns": envelope.get("num_turns"),
        "denials": len(envelope.get("permission_denials") or []), "left_in_box": left,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
        "seconds": round(time.time() - started),
    }
    xr._json(record, rec)
    return rec


def judge_prompt(pair: Path, problems: list[dict[str, Any]]) -> str:
    """판정 머리말 + 쌍의 파일 넷 (감사와 같은 꼴) + 재현된 지적과 그 출력. 측정값은 없다."""
    parts = [audit_prompt(pair, JUDGE_HEAD.read_text(encoding="utf-8").rstrip())]
    for n, p in enumerate(problems, 1):
        out = [f"stdout:\n{p['stdout_tail'].rstrip()}"]
        if p["stderr_tail"].strip():
            out.append(f"stderr:\n{p['stderr_tail'].rstrip()}")
        parts.append(
            f"=== 지적 {n} — {p['kind']} · decoy.py {p['lines']} ===\n{p['summary']}\n\n"
            f"근거: {p['evidence']}\n\n재현 스크립트:\n```python\n{p['repro'].rstrip()}\n```\n\n"
            "하네스의 실행 출력 (끝 20줄):\n```text\n" + "\n".join(out) + "\n```"
        )
    return "\n\n".join(parts)


def run_pair(pair: Path, out: Path, model: str) -> None:
    """감사 → 재현 (마지막 줄이 정확히 REPRODUCED) → 재현된 지적이 있으면 판정 A · B."""
    d = out / pair.name
    d.mkdir(parents=True, exist_ok=True)
    head = xr.AUDIT_HEAD.read_text(encoding="utf-8").rstrip()
    rec = session(
        d, "audit", audit_prompt(pair, head), schema=xr.AUDIT_SCHEMA, key="findings",
        model=model, check=xr.findings_of,
    )
    rep = d / "audit.repro.json"
    if not rep.exists():
        xr._json(rep, [xr.repro_one(pair, f, VENV) for f in rec["answer"]])
    problems = [f for f in xr._load(rep) if f["reproduced"]]
    if not problems:
        return
    prompt = judge_prompt(pair, problems)
    for j in JUDGES:
        session(
            d, f"judge-{j}", prompt, schema=JUDGE_SCHEMA, key="verdicts", model=model,
            check=lambda last: verdicts_of(last, len(problems)),
        )


def label_issues(out: Path, pairs: list[Path]) -> dict[str, list[str]]:
    """판정자마다 IN 이 하나라도 있는 쌍 - `xauthor-report` 의 민감도가 읽는 목록."""
    found: dict[str, list[str]] = {j: [] for j in JUDGES}
    for pair in pairs:
        for j in JUDGES:
            rec = out / pair.name / f"judge-{j}.json"
            if rec.exists() and any(v["verdict"] == "IN" for v in xr._load(rec)["answer"]):
                found[j].append(pair.name)
    return found


def write_issues(root: Path, found: dict[str, list[str]], refused: list[str]) -> None:
    """판정은 한 번이다 - 이미 다른 목록이 있으면 덮지 않고 멈춘다."""
    root.mkdir(parents=True, exist_ok=True)
    for j, names in found.items():
        path = root / f"claude-audit-{j}.txt"
        head = f"# claude 감사 판정자 {j} - IN 이 하나라도 있는 쌍 (DESIGN §7.10d)\n"
        notes = "".join(f"# 거절된 세션이 있는 쌍: {n}\n" for n in refused)
        body = head + notes + "".join(f"{n}\n" for n in names)
        if path.exists() and path.read_text(encoding="utf-8") != body:
            raise Stop(HUMAN, f"{path} 에 다른 목록이 있다 - 판정은 한 번이다")
        path.write_text(body, encoding="utf-8")


def _cut(d: Path, usage: Counter[str]) -> int:
    """cut/ 으로 옮긴 세션 수 - 봉투를 읽을 수 있으면 그 사용량도 더한다 (호출은 났다)."""
    reasons = sorted((d / "cut").glob("*.reason")) if (d / "cut").is_dir() else []
    for q in reasons:
        try:
            envelope = json.loads(q.with_suffix(".claude.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for k, v in ((envelope.get("usage") or {}) if isinstance(envelope, dict) else {}).items():
            if isinstance(v, int):
                usage[k] += v
    return len(reasons)


def summarize(out: Path) -> dict[str, Any]:
    """세션 · 지적 · 재현 · 판정 · 두 판정자의 일치 - 사용량은 필드마다 따로 더한다 (D2).

    `sessions` 는 기록된 세션, `cut_sessions` 는 cut/ 으로 옮긴 호출 (읽지 못한 답 · 시간 초과 ·
    끊김)이다 - 둘 다 구독 사용량이라 `cut_usage` 를 따로 싣는다.
    """
    usage: Counter[str] = Counter()
    cut_usage: Counter[str] = Counter()
    verdicts: dict[str, Counter[str]] = {j: Counter() for j in JUDGES}
    pairs = findings = reproduced = agree = compared = sessions = cut_sessions = 0
    refused: list[str] = []
    for d in sorted(p for p in out.iterdir() if p.is_dir()):
        cut_sessions += _cut(d, cut_usage)
        if not (d / "audit.json").is_file():
            continue
        pairs += 1
        recs = {s: xr._load(d / f"{s}.json") for s in ("audit", *(f"judge-{j}" for j in JUDGES))
                if (d / f"{s}.json").is_file()}
        for s, rec in recs.items():
            sessions += 1
            if rec["refused"]:
                refused.append(f"{d.name} {s}")
            for k, v in (rec.get("usage") or {}).items():
                if isinstance(v, int):
                    usage[k] += v
        findings += len(recs["audit"]["answer"])
        if (d / "audit.repro.json").is_file():
            reproduced += sum(1 for f in xr._load(d / "audit.repro.json") if f["reproduced"])
        got = {j: recs[f"judge-{j}"] for j in JUDGES if f"judge-{j}" in recs}
        for j, rec in got.items():
            verdicts[j].update(v["verdict"] for v in rec["answer"])
        if len(got) == len(JUDGES) and not any(r["refused"] for r in got.values()):
            for a, b in zip(*(r["answer"] for r in got.values()), strict=True):
                compared += 1
                agree += a["verdict"] == b["verdict"]
    return {
        "pairs": pairs, "sessions": sessions, "cut_sessions": cut_sessions,
        "findings": findings, "reproduced": reproduced,
        "verdicts": {j: dict(c) for j, c in verdicts.items()},
        "agreement": f"{agree}/{compared}", "refused": refused, "usage": dict(usage),
        "cut_usage": dict(cut_usage),
    }


def cli_version() -> str:
    """고정한 claude 의 판 - 설치가 없으면 빈 문자열 (preflight 가 멈춘다)."""
    try:
        done = subprocess.run(  # noqa: S603 - 고정 경로의 claude
            [str(CLAUDE), "--version"], capture_output=True, text=True, env=environment(),
            check=False,
        )
    except OSError:
        return ""
    return done.stdout.strip()


def signed(model: str) -> dict[str, str]:
    return {
        "cli": CLAUDE_VERSION, "model": model, "effort": EFFORT, "flags": " ".join(FLAGS),
        "env": " ".join(f"{k}={v}" for k, v in sorted(SWITCHES.items())),
        "audit_head_sha256": xr._sha256(xr.AUDIT_HEAD),
        "audit_schema_sha256": xr._sha256(xr.AUDIT_SCHEMA),
        "judge_head_sha256": xr._sha256(JUDGE_HEAD),
        "judge_schema_sha256": xr._sha256(JUDGE_SCHEMA),
        "prompt_builder_sha256": xr._sha256(REPO / "scripts" / "cross_family_prompt.py"),
        "profile": xa.profile(Path("<venv>")),
    }


def harness_reproduces(pair: Path) -> bool:
    """재현 하네스 자기 점검 (모델 없이) - REPRODUCED 만 찍는 스크립트가 재현돼야 한다.

    🔴 sandbox · venv 가 깨지면 모든 재현이 「재현 안 됨」으로 기록되고, 판정 없이 빈 목록이
       굳는다 (판정은 한 번이다). 감사는 2단계에서 며칠 뒤 돈다 - 시작 전에 한 번 본다.
    """
    probe = {"kind": "probe", "lines": "1", "summary": "-", "evidence": "-",
             "repro": 'print("REPRODUCED")\n'}
    return bool(xr.repro_one(pair, probe, VENV)["reproduced"])


def preflight(out: Path, model: str, *, canary: bool, probe: Path) -> None:
    """고정 문서 · venv · 재현 하네스 · RUN.json - 하나라도 어긋나면 시작하지 않는다."""
    if (found := cli_version()) != CLAUDE_VERSION:
        raise Stop(HUMAN, f"claude 판이 다르다: {found!r} (선언 {CLAUDE_VERSION})")
    fixed = (xr._sha256(xr.AUDIT_HEAD), xr._sha256(JUDGE_HEAD))
    if fixed != (xr.AUDIT_HEAD_SHA256, JUDGE_HEAD_SHA256):
        raise Stop(HUMAN, "고정 문서가 커밋한 판과 다르다 - audit_head.md · judge_head.md")
    if not (VENV / "bin" / "python").exists():
        raise Stop(HUMAN, f"재현 venv 가 없다 - {VENV}")
    if not harness_reproduces(probe):
        why = "재현 하네스가 확실한 재현을 재현하지 못했다 - codex sandbox · venv 를 본다"
        raise Stop(HUMAN, why)
    fields = signed(model)
    run_json = out / "RUN.json"
    if run_json.exists():
        rec = xr._load(run_json)
        if diffs := [k for k in SIGNED if rec.get(k) != fields[k]]:
            raise Stop(HUMAN, f"RUN.json 의 설정과 다르다: {diffs}")
        if rec.get("canary") != canary:
            raise Stop(HUMAN, "카나리와 본 실행은 출력 디렉터리를 나눈다")
    else:
        rec = {
            "what": "DESIGN §7.10d 「측정 뒤 claude 감사」" + (" - 카나리" if canary else ""),
            "canary": canary, **fields, "judges": list(JUDGES), "timeout_s": TIMEOUT_S,
            "invocations": [],
        }
    rec["invocations"].append({
        "at": xr._now(), "commit": xr._git("rev-parse", "HEAD"),
        "runner_sha256": xr._sha256(Path(__file__)),
    })
    xr._json(run_json, rec)


def run(
    out: Path, *, canary: bool = False, corpus: Path = CORPUS, agents: Path = AGENTS,
    issues: Path = ISSUES,
) -> int:
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / ".lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("rc=4 · 이 출력 디렉터리에서 다른 실행기가 돌고 있다", file=sys.stderr)
        return HUMAN
    try:
        model = accepted_model()
        if canary:
            pairs = [p for p in pair_dirs(CANARY) if p.name.startswith(f"{CANARY_PAIR}-")]
        else:
            got = measured_model(corpus, agents)
            if got is None:
                raise Stop(HUMAN, "측정 전이다 - 두 묶음이 코퍼스의 쌍 전부를 잰 뒤에 돈다")
            if got != model:
                raise Stop(HUMAN, f"측정한 claude({got}) 와 받아들인 모델({model}) 이 다르다")
            pairs = pair_dirs(corpus)
        if not pairs:
            raise Stop(HUMAN, "감사할 쌍이 없다")
        preflight(out, model, canary=canary, probe=pairs[0])
        for pair in pairs:
            run_pair(pair, out, model)
        summary = summarize(out)
        if not canary:
            write_issues(issues, label_issues(out, pairs), summary["refused"])
    except Stop as stop:
        print(f"rc={stop.rc} · {stop}", file=sys.stderr)
        return stop.rc
    xr._json(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return DONE


def main(argv: list[str]) -> int:
    match argv:
        case [out, "--summary"]:
            print(json.dumps(summarize(Path(out).resolve()), ensure_ascii=False, indent=2))
            return DONE
        case [out, *rest] if rest in ([], ["--canary"]):
            signal.signal(signal.SIGTERM, lambda *_: sys.exit(128 + signal.SIGTERM))
            return run(Path(out).resolve(), canary=bool(rest))
        case _:
            print(__doc__, file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
