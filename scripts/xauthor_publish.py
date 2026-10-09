"""작성 기록을 공개할 판으로 묶는다 - DESIGN §7.10d 「공개」 (경로를 가리고 비밀을 훑은 뒤).

    uv run python scripts/xauthor_publish.py --check <기록 폴더>...   훑기만 한다
    uv run python scripts/xauthor_publish.py --out <폴더> <기록 폴더>...
        → <폴더>/<기록 폴더 이름>.jsonl (줄마다 {"path", "text"} · 경로를 가린 판 · 경로 순)

가리는 것: 저장소 → `<repo>` · 홈 → `~` · /Users/Shared → `<shared>` · macOS 임시 폴더 → `<tmp>`.
훑는 것은 가린 뒤의 글이다 - 키 · 토큰 · 개인 키 · 인증 필드 · 예시가 아닌 이메일. 하나라도 보이면
아무것도 쓰지 않고 (파일:줄 · 종류)만 보인다 - 일치한 글은 찍지 않는다.

🔴 push 는 되돌릴 수 없다 - 이 도구가 막지 못한 것은 공개 전에 사람이 본다. 패턴은 바닥선이다.
🔴 같은 기록이면 같은 바이트를 낸다 - 다시 묶어도 공개본이 흔들리지 않는다 (F5b 와 같은 이유).
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKIP = re.compile(r"(^|/)(__pycache__|\.lock$|\.DS_Store$)")
MASKS = (
    (re.compile(r"(/private)?/var/folders/[^\s\"'\\]+"), "<tmp>"),
    (re.compile(re.escape(str(REPO))), "<repo>"),
    (re.compile(re.escape(str(Path.home()))), "~"),
    (re.compile(r"/Users/Shared(?=/|\b)"), "<shared>"),
)
"""순서가 뜻이다 - 저장소는 홈 아래라 먼저 가린다."""
SECRETS = {
    "API 키 (sk-)": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\."),
    "GitHub 토큰": re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "AWS 키": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack 토큰": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "개인 키": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Bearer 토큰": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}"),
    "인증 필드": re.compile(r'"(access_token|refresh_token|id_token|api_key|account_id)"\s*:'),
    "이메일": re.compile(
        r"[A-Za-z0-9._%+-]+@(?!(?:example\.(?:com|org|net)|[\w-]+\.(?:test|invalid|example))\b)"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"
    ),
}
"""[실측 · 1·2단계 기록 1120파일] 가린 뒤 0건 - Homebrew 경로의 python@3.14 는 이메일이 아니다."""


def mask(text: str) -> str:
    for pattern, to in MASKS:
        text = pattern.sub(to, text)
    return text


def records(root: Path) -> list[tuple[str, str]]:
    """(기록 폴더 안의 경로, 가린 글) - 경로 순. 글이 아닌 파일은 거절한다 (가릴 수 없다)."""
    out = []
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = f.relative_to(root).as_posix()
        if SKIP.search(rel):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            msg = f"{root.name}/{rel} 가 UTF-8 글이 아니다 - 가릴 수 없어 묶지 않는다"
            raise ValueError(msg) from exc
        out.append((rel, mask(text)))
    return out


def findings(root: Path, rows: list[tuple[str, str]]) -> list[str]:
    """가린 글에 남은 비밀 - (파일:줄 · 종류)만. 일치한 글은 내지 않는다."""
    found = []
    for rel, text in rows:
        for n, line in enumerate(text.split("\n"), 1):
            found += [f"{root.name}/{rel}:{n} · {kind}" for kind, p in SECRETS.items()
                      if p.search(line)]
    return found


def publish(roots: list[Path], out: Path | None) -> list[str]:
    """훑고, 아무것도 없을 때만 쓴다 - 임시 파일에 쓴 뒤 이름을 바꾼다."""
    bundles = {root: records(root) for root in roots}
    found = [f for root, rows in bundles.items() for f in findings(root, rows)]
    if found or out is None:
        return found
    out.mkdir(parents=True, exist_ok=True)
    for root, rows in bundles.items():
        body = "".join(
            json.dumps({"path": rel, "text": text}, ensure_ascii=False) + "\n" for rel, text in rows
        )
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=out, delete=False, suffix=".tmp"
        ) as tmp:
            tmp.write(body)
        Path(tmp.name).replace(out / f"{root.name}.jsonl")
    return found


def main(argv: list[str]) -> int:
    match argv:
        case ["--check", *roots] if roots:
            out = None
        case ["--out", target, *roots] if roots:
            out = Path(target)
        case _:
            print(__doc__, file=sys.stderr)
            return 2
    try:
        found = publish([Path(r) for r in roots], out)
    except ValueError as exc:
        print(f"rc=4 · {exc}", file=sys.stderr)
        return 4
    if found:
        print(f"rc=4 · 비밀로 보이는 것 {len(found)}건 - 아무것도 쓰지 않았다", file=sys.stderr)
        for line in found[:50]:
            print(f"  {line}", file=sys.stderr)
        return 4
    print("비밀로 보이는 것 0건" + (f" · {out} 에 썼다" if out else " (--check · 쓰지 않았다)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
