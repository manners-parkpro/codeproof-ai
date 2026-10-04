"""review-with-agent.sh 의 판정 로직 - **표준 라이브러리만** 쓴다.

실행 흐름은 셸에 두고, 틀리면 숫자가 틀리는 판단은 여기 둔다. 셸 heredoc 에
묻어 두면 에이전트 없이 시험할 방법이 없다 - `tests/scripts/` 가 이 파일을
직접 불러 깨뜨려 본다 (H3).

    resolve-claude <probe.json>             응답의 modelUsage -> 실제 모델 ID
    resolve-codex <effort> [model]          stdin 의 카탈로그 -> 최상위 공개 모델
    record <RUN.json> key=value ...         실행 기록. 🔴 기존 기록과 설정이 다르면 거부
    finish <RUN.json> key=value ...         실행 끝 정보를 덧붙인다
    digests <MANIFEST.json> <export-dir>    샘플 디렉터리마다 지문이 있는가 (시작 때 한 번)
    extract <agent> <raw-prefix> <model> <dest> <MANIFEST.json> <sample_id>
                                            원본 -> {"findings": [...]} + 잰 코드의 지문 옆 파일
    audit <out-dir>                         상자 밖 접근 흔적
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# 🔴 실행 설정. 하나라도 다르면 같은 출력 디렉터리에 이어 쓰지 않는다 -
#    섞이면 한 실행이 아니다 (F1). timeout 은 측정 조건이 아니라 운영 값이라 뺀다.
#    반복 횟수(runs)도 뺀다 - 조건이 아니라 **표본 크기**다. 같은 조건의 호출은
#    서로 교환 가능하므로 1회 파일럿을 F8 의 8회로 늘려 이어 쓸 수 있다.
#    ⚠ 결과를 보고 늘리면 optional stopping 이다 (F5a). 목표는 미리 정한 값이어야
#      하고, 늘린 이력은 sessions 에 남는다.
CONFIG_KEYS = (
    "runner_version",
    "agent",
    "cli_version",
    "model_requested",
    "model",
    "effort",
    "isolation",
    "permission",
    "prompt_hash",
    "instruction_hash",
    "schema_hash",
    "docstrings",  # 입력 코드가 달라지는 손잡이 (DESIGN §7.10c)
)

# 상자(무작위 임시 디렉터리) 밖을 봤다는 흔적. 🔴 실행을 막지 않고 **센다** -
# 에이전트는 파일 탐색이 가능하므로 라벨(meta.toml)에 닿을 수 있었는지는
# 사후에 확인할 수밖에 없다. 상자 자신의 경로는 검사 전에 지운다 (`<prefix>.box`).
SUSPICIOUS = re.compile(
    r"(^|[\s'\"=(])/"  # 상자 경로를 지운 뒤 남은 절대경로는 전부 상자 밖이다
    r"|\$HOME|(^|\s)~(/|\s|$)"
    r"|(^|[\s'\"=/])\.\.(/|[\s'\"]|$)"
    r"|codeproof|corpus|meta\.toml|decoy|twin|agent-(in|out)"
)
# 명령을 감싼 셸 자체(/bin/zsh -lc ...)는 접근이 아니다.
_SHELL = re.compile(r"^/bin/(?:ba|z)?sh\s+-\w*c\s+")


class RefusedError(Exception):
    """판정 불가 - 호출은 실패로 센다."""


_DIGEST = re.compile(r"[0-9a-f]{64}")


def measured_digest(manifest: Path, sample_id: str) -> str:
    """이 샘플로 내보낸 코드의 지문 (`codeproof export` 가 MANIFEST 에 싣는다).

    🔴 회차마다 옆 파일(`<sample_id>.<run>.digest`)로 옮겨 적는다. 출력에는 지적만 있어 무엇을
       쟀는지 남지 않았고, 고친 샘플만 다시 잴 때 옛 출력이 하나라도 남으면 pack 이 그것을
       **지금** 코드의 지문으로 조용히 묶었다 (DESIGN §9 의 5). pack 이 이 파일로 견준다.
    """
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for row in data.get("samples", []):
        if isinstance(row, dict) and row.get("sample_id") == sample_id:
            digest = row.get("digest")
            if isinstance(digest, str) and _DIGEST.fullmatch(digest):
                return digest
    msg = f"{manifest} 에 {sample_id} 의 지문이 없다 - codeproof export 로 다시 내보낸다"
    raise RefusedError(msg)


def last_findings_object(text: str) -> dict[str, object] | None:
    """산문·펜스가 섞인 출력에서 `findings` 배열을 가진 **마지막** 객체.

    앞쪽은 프롬프트 반향일 수 있다 - 규격 예시도 `{"findings": [...]}` 모양이다.
    """
    best: dict[str, object] | None = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[i : j + 1])
                    except ValueError:
                        pass
                    else:
                        if isinstance(obj, dict) and isinstance(obj.get("findings"), list):
                            best = obj
                    break
    return best


def _models_in(envelope: dict[str, object]) -> set[str]:
    usage = envelope.get("modelUsage")
    if not isinstance(usage, dict):
        return set()
    out: set[str] = set()
    for key, entry in usage.items():
        out.add(str(key))
        if isinstance(entry, dict) and entry.get("canonicalModel"):
            out.add(str(entry["canonicalModel"]))
    return out


def resolve_claude(envelope: dict[str, object]) -> str:
    """`--model best`(또는 별칭) 호출의 응답에서 실제로 답한 모델 ID.

    보조 작업에 작은 모델이 섞일 수 있으므로 출력 토큰이 가장 많은 것을 고른다.
    """
    if envelope.get("is_error"):
        detail = f"{envelope.get('subtype')} {str(envelope.get('result'))[:200]}"
        raise RefusedError(f"해석 호출이 실패했다: {detail}")
    usage = envelope.get("modelUsage")
    if not isinstance(usage, dict) or not usage:
        raise RefusedError("modelUsage 가 없다 - 어떤 모델이 답했는지 알 수 없다")
    key, entry = max(
        usage.items(),
        key=lambda kv: kv[1].get("outputTokens", 0) if isinstance(kv[1], dict) else 0,
    )
    if isinstance(entry, dict) and entry.get("canonicalModel"):
        return str(entry["canonicalModel"])
    return str(key)


def resolve_codex(catalog: object, effort: str, model: str | None = None) -> str:
    """카탈로그에서 모델을 고른다. 🔴 effort 를 지원하지 않으면 거부한다.

    `model` 을 주면 그 모델이 있는지·effort 를 지원하는지만 본다. 없으면
    공개(`visibility == "list"`) 모델 중 `priority` 가 가장 앞선 것 - 벤더 자신의
    순위다. 우리가 「최고」를 정하지 않는다.
    """
    models = catalog.get("models") if isinstance(catalog, dict) else catalog
    if not isinstance(models, list) or not models:
        raise RefusedError("모델 카탈로그를 읽지 못했다")

    def efforts(m: dict[str, object]) -> set[str]:
        levels = m.get("supported_reasoning_levels") or []
        return {str(lv.get("effort")) for lv in levels if isinstance(lv, dict)}

    if model:
        hit = next((m for m in models if isinstance(m, dict) and m.get("slug") == model), None)
        if hit is None:
            raise RefusedError(f"카탈로그에 없는 모델: {model}")
        if effort not in efforts(hit):
            supported = sorted(efforts(hit))
            raise RefusedError(f"{model} 은 effort={effort} 를 지원하지 않는다: {supported}")
        return model

    listed = [m for m in models if isinstance(m, dict) and m.get("visibility") == "list"]
    if not listed:
        raise RefusedError("공개 모델이 없다")
    top = min(listed, key=lambda m: m.get("priority", 10**9))
    if effort not in efforts(top):
        raise RefusedError(f"최상위 모델 {top.get('slug')} 은 effort={effort} 를 지원하지 않는다")
    return str(top["slug"])


def describe_codex(catalog: object, slug: str) -> str:
    """카탈로그에 적힌 그 모델의 설명. 없으면 빈 문자열 - 판정이 아니라 기록용이다."""
    models = catalog.get("models") if isinstance(catalog, dict) else catalog
    for m in models if isinstance(models, list) else []:
        if isinstance(m, dict) and m.get("slug") == slug:
            return str(m.get("description") or "")
    return ""


def check_model(
    lock: Path, agent: str, model: str, note: str = "", *, accept: bool = False
) -> str | None:
    """🔴 벤더의 최상위가 바뀌면 조용히 따라가지 않는다.

    「최상위 모델」은 벤더가 정하고 우리는 순위를 매기지 않는다(DESIGN §7.10). 대신 새 실행이
    지난번에 받아들인 모델과 **다른** 모델로 해석되면 멈춘다 - 실험 사이에 측정 대상이
    바뀌는 것은 사람이 알고 정할 일이다. [실측 2026-09-30] 0.159 클라이언트가 받은
    카탈로그에서 priority 0 은 일상용 모델("workhorse")이었다 - CLI 를 올리는 순간
    새 실행이 에러 없이 바뀐다.

    `lock` 은 에이전트별로 받아들인 모델과 그 설명을 적는다. 항목이 없으면 기록하고 통과한다.

    Returns:
        None 이면 통과. 문자열이면 거부 사유 - 호출부가 멈춘다.
    """
    data = json.loads(lock.read_text(encoding="utf-8")) if lock.is_file() else {}
    prev = data.get(agent)
    if isinstance(prev, dict) and prev.get("model") != model and not accept:
        return (
            f"벤더 최상위가 바뀌었다: {prev.get('model')} ({prev.get('note', '')})"
            f" -> {model} ({note})\n"
            f"   기준을 지키려면 --model {prev.get('model')} 로 명시한다.\n"
            "   받아들이려면 ACCEPT_MODEL_CHANGE=1 로 다시 돌려 기준을 갱신한다."
        )
    if not isinstance(prev, dict) or prev.get("model") != model:
        data[agent] = {"model": model, "note": note}
        tmp = lock.with_suffix(lock.suffix + ".tmp")
        body = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(lock)
    return None


def _session(fields: dict[str, str]) -> dict[str, str]:
    return {k: fields.get(k, "") for k in ("started_at", "runs", "runner_sha")}


def record(path: Path, fields: dict[str, str]) -> list[str]:
    """실행 기록을 쓴다. 이미 있으면 **설정이 같은지** 확인하고 세션을 덧붙인다.

    이어 쓰기마다 `sessions` 에 (시각 · 목표 반복 횟수 · 실행기 커밋) 을 남긴다 -
    한 디렉터리의 출력이 언제 어떤 실행기로 쌓였는지 나중에 물을 수 있게.

    Returns:
        불일치 목록. 비어 있지 않으면 호출부가 거부한다 (파일은 건드리지 않는다).
    """
    if not path.is_file():
        data: dict[str, object] = dict(fields)
        data["sessions"] = [_session(fields)]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return []
    old = json.loads(path.read_text(encoding="utf-8"))
    diffs = [
        f"{k}: 기록={old.get(k)!r} 지금={fields.get(k)!r}"
        for k in CONFIG_KEYS
        if str(old.get(k)) != str(fields.get(k))
    ]
    if diffs:
        return diffs
    sessions = old.get("sessions") or [
        # 세션 기록이 생기기 전의 실행 - 알던 것만 옮긴다
        {"started_at": old.get("started_at", ""), "runs": str(old.get("runs", "")),
         "runner_sha": old.get("runner_sha", "unknown")}
    ]
    sessions.append(_session(fields))
    old["sessions"] = sessions
    counts = [int(s["runs"]) for s in sessions if str(s.get("runs", "")).isdigit()]
    if counts:
        old["runs"] = str(max(counts))
    path.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return []


def finish(path: Path, fields: dict[str, str]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    for k, v in fields.items():
        # 감사 결과처럼 JSON 으로 넘어온 값은 문자열이 아니라 구조로 싣는다.
        try:
            data[k] = json.loads(v) if v.startswith("{") else v
        except ValueError:
            data[k] = v
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_claude(envelope: dict[str, object], model: str) -> tuple[dict[str, object], str]:
    if envelope.get("is_error"):
        detail = f"{envelope.get('subtype')} {str(envelope.get('result'))[:200]}"
        raise RefusedError(f"is_error: {detail}")
    # 🔴 다른 모델이 답했으면 측정 대상이 바뀐 것이다 (D5 의 fallbacks 와 같은 이유).
    seen = _models_in(envelope)
    if model not in seen:
        raise RefusedError(f"고정한 모델이 답하지 않았다: 고정={model} 응답={sorted(seen)}")
    payload = envelope.get("structured_output")
    if not (isinstance(payload, dict) and isinstance(payload.get("findings"), list)):
        payload = last_findings_object(str(envelope.get("result") or ""))
    if payload is None:
        raise RefusedError("findings 를 찾지 못했다")
    denials = envelope.get("permission_denials") or []
    meta = f"turns={envelope.get('num_turns')} denials={len(denials)}"
    return payload, meta


def extract_codex(last_message: str, events: str) -> tuple[dict[str, object], str]:
    payload: dict[str, object] | None
    try:
        obj = json.loads(last_message)
        payload = obj if isinstance(obj, dict) and isinstance(obj.get("findings"), list) else None
    except ValueError:
        payload = None
    if payload is None:
        payload = last_findings_object(last_message)
    if payload is None:
        # [실측] 크레딧 소진이 「findings 를 찾지 못했다」로만 보였다 - 원인을 올린다.
        error = _codex_error(events)
        if error:
            raise RefusedError(f"codex 오류: {error}")
        raise RefusedError("마지막 메시지에서 findings 를 찾지 못했다")
    cmds = sum(1 for c in _codex_commands(events))
    return payload, f"cmds={cmds}"


def _codex_error(events: str) -> str | None:
    """JSONL 의 마지막 오류 메시지 (`error` · `turn.failed`)."""
    found: str | None = None
    for line in events.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        if e.get("type") == "error" and e.get("message"):
            found = str(e["message"])
        elif e.get("type") == "turn.failed":
            err = e.get("error")
            if isinstance(err, dict) and err.get("message"):
                found = str(err["message"])
    return found


def _codex_commands(events: str) -> list[str]:
    out: list[str] = []
    for line in events.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        item = e.get("item") if isinstance(e, dict) else None
        if (
            e.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("type") == "command_execution"
        ):
            out.append(str(item.get("command", "")))
    return out


def audit(out_dir: Path) -> dict[str, list[str]]:
    """상자 밖 접근 흔적 - 샘플별로 의심 명령을 모은다.

    codex 는 JSONL 에 실행한 명령이 전부 남는다. claude 는 읽기 도구만 있고
    dontAsk 라서 cwd 밖 접근은 거부되어 `permission_denials` 에 남는다.
    """
    hits: dict[str, list[str]] = {}
    raw = out_dir / "raw"
    for f in sorted(raw.glob("*.jsonl")):
        box_file = Path(str(f)[: -len(".jsonl")] + ".box")
        box = box_file.read_text(encoding="utf-8").strip() if box_file.is_file() else ""
        for cmd in _codex_commands(f.read_text(encoding="utf-8", errors="replace")):
            seen = _SHELL.sub("", cmd)
            if box:
                # macOS 는 /var 가 /private/var 의 링크다 - 둘 다 상자다.
                seen = seen.replace("/private" + box, "<box>").replace(box, "<box>")
            if SUSPICIOUS.search(seen):
                hits.setdefault(f.name, []).append(cmd[:200])
    for f in sorted(raw.glob("*.claude.json")):
        try:
            env = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        denials = env.get("permission_denials") if isinstance(env, dict) else None
        if denials:
            hits.setdefault(f.name, []).extend(
                json.dumps(d, ensure_ascii=False)[:200] for d in denials
            )
    return hits


def _kv(args: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for a in args:
        k, _, v = a.partition("=")
        out[k] = v
    return out


def _model_guard_command(cmd: str, rest: list[str]) -> int:
    """모델 기준 확인 명령. 모르는 명령이면 2. 예외는 main 이 받는다."""
    if cmd == "describe-codex":
        catalog = json.loads(Path(rest[1]).read_text(encoding="utf-8"))
        print(describe_codex(catalog, rest[0]))
        return 0
    if cmd == "check-model":
        lock, agent, model, *note = rest
        accept = os.environ.get("ACCEPT_MODEL_CHANGE") == "1"
        reason = check_model(Path(lock), agent, model, note[0] if note else "", accept=accept)
        if reason:
            print(reason)
            return 4
        return 0
    print(f"모르는 명령: {cmd}", file=sys.stderr)
    return 2


def extract(argv: list[str]) -> str:
    """원본 -> `<dest>` ({"findings": [...]}) + 옆에 잰 코드의 지문. 돌려주는 값은 진행 표시줄.

    argv: `<agent> <raw-prefix> <model> <dest> <MANIFEST.json> <sample_id>` - 실행기의 인자 그대로.
    """
    agent, prefix, model, dest, manifest, sample_id = argv
    digest = measured_digest(Path(manifest), sample_id)  # 원본보다 먼저 - 없으면 아무것도 안 쓴다
    if agent == "claude":
        env = json.loads(Path(prefix + ".claude.json").read_text(encoding="utf-8"))
        payload, meta = extract_claude(env, model)
    else:
        last = Path(prefix + ".last.json")
        events = Path(prefix + ".jsonl")
        payload, meta = extract_codex(
            last.read_text(encoding="utf-8") if last.is_file() else "",
            events.read_text(encoding="utf-8") if events.is_file() else "",
        )
    # 🔴 지문을 출력보다 먼저 쓴다 - 출력이 있으면 지문도 있다. 사이에서 끊기면 출력이 없어
    #    다음 세션이 그 회차를 다시 재고 지문을 덮어쓴다.
    side = Path(dest).with_suffix(".digest")
    side_tmp = side.with_name(side.name + ".tmp")
    side_tmp.write_text(digest + "\n", encoding="utf-8")
    side_tmp.replace(side)
    tmp = Path(dest + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dest)  # 🔴 원자적으로 - 반쯤 쓴 파일이 「완료」로 읽히지 않게
    return f"{len(payload['findings'])} {meta}"  # type: ignore[arg-type]


def main(argv: list[str]) -> int:
    cmd, *rest = argv
    try:
        if cmd == "resolve-claude":
            print(resolve_claude(json.loads(Path(rest[0]).read_text(encoding="utf-8"))))
        elif cmd == "resolve-codex":
            print(resolve_codex(json.load(sys.stdin), rest[0], rest[1] if len(rest) > 1 else None))
        elif cmd == "record":
            diffs = record(Path(rest[0]), _kv(rest[1:]))
            if diffs:
                print("\n".join(diffs))
                return 3
        elif cmd == "finish":
            finish(Path(rest[0]), _kv(rest[1:]))
        elif cmd == "digests":
            boxes = sorted(p.name for p in Path(rest[1]).iterdir() if p.is_dir())
            for sid in boxes:
                measured_digest(Path(rest[0]), sid)
            print(len(boxes))
        elif cmd == "extract":
            print(extract(rest))
        elif cmd == "audit":
            hits = audit(Path(rest[0]))
            print(json.dumps({"files": len(hits), "hits": hits}, ensure_ascii=False))
        else:
            return _model_guard_command(cmd, rest)
    except RefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
