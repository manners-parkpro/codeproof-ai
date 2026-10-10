"""작성 기록을 공개할 판으로 묶는다 - DESIGN §7.10d 「공개」 (경로를 가리고 비밀을 훑은 뒤).

    uv run python scripts/xauthor_publish.py --check <기록 폴더>...   훑기만 한다
    uv run python scripts/xauthor_publish.py --out <폴더> <기록 폴더>...
        → <폴더>/<기록 폴더 이름>.jsonl (줄마다 {"path", "text"} · 경로를 가린 판 · 경로 순)

가리는 것: 저장소 → `<repo>` · 홈 → `~` · /Users/Shared → `<shared>` · macOS 임시 폴더 → `<tmp>` ·
계정 이름 → `<user>` (`ls -l` 의 소유자 열). 훑는 것은 가린 뒤의 글이다 - 키 · 토큰 · 개인 키 ·
인증 필드 · 계정 식별자 · 예시가 아닌 이메일 · 가리지 못한 홈 경로. 하나라도 보이면 아무것도 쓰지
않고 (파일:줄 · 종류)만 보인다 - 일치한 글은 찍지 않는다.

🔴 기록의 주 형식은 JSON 이스케이프된 글이다 (codex 이벤트의 명령 출력 · 봉투) - 패턴은 `\\n` ·
   `\\t` · `\\uXXXX` 바로 뒤를 낱말 경계로 보고 `\\"키\\":` 꼴도 맞춘다.
🔴 push 는 되돌릴 수 없다 - 이 도구가 막지 못한 것은 공개 전에 사람이 본다. 패턴은 바닥선이다.
🔴 같은 기록이면 같은 바이트를 낸다 - 어느 체크아웃 · 어떤 HOME 에서 돌려도 (F5b 와 같은 이유).
"""

from __future__ import annotations

import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo() -> Path:
    """저장소의 주 체크아웃 - worktree 의 사본에서 돌려도 같은 경로를 `<repo>` 로 가린다."""
    here = Path(__file__).resolve().parents[1]
    git = shutil.which("git")
    if git is None:
        return here
    done = subprocess.run(  # noqa: S603 - PATH 에서 찾은 git
        [git, "-C", str(here), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, check=False,
    )
    return Path(done.stdout.strip()).parent if done.returncode == 0 else here


REPO = _repo()
ACCOUNT = pwd.getpwuid(os.getuid())
"""OS 계정 - $HOME 을 바꾼 셸에서도 계정의 홈 · 이름을 가린다."""
SKIP = re.compile(r"(^|/)(__pycache__|\.lock$|\.DS_Store$)")
MASKS = (
    (re.compile(r"(/private)?/var/folders/[^\s\"'\\]+"), "<tmp>"),
    (re.compile(re.escape(str(REPO))), "<repo>"),
    *(
        (re.compile(re.escape(home)), "~")
        for home in sorted({ACCOUNT.pw_dir, str(Path.home())}, key=len, reverse=True)
    ),
    (re.compile(r"/Users/Shared(?=/|\b)"), "<shared>"),
    (re.compile(rf"(?<![\w.-]){re.escape(ACCOUNT.pw_name)}(?![\w-])"), "<user>"),
)
"""순서가 뜻이다 - 저장소는 홈 아래라 먼저 가리고, 계정 이름은 경로를 가린 뒤에 남은 것만."""
_B = r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=\\u[0-9a-fA-F]{4}))"
"""낱말 경계 - 이스케이프가 남긴 n · t · r · 16진 숫자는 낱말 문자라 `\\b` 가 놓친다."""
_Q = r'\\?"'
"""따옴표 - 글 안의 JSON 은 `\\"` 로 온다."""
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
SECRETS = {
    "API 키 (sk-)": re.compile(_B + r"sk-[A-Za-z0-9_-]{16,}"),
    "JWT": re.compile(_B + r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\."),
    "GitHub 토큰": re.compile(_B + r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "AWS 키": re.compile(_B + r"AKIA[0-9A-Z]{16}\b"),
    "Slack 토큰": re.compile(_B + r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    "개인 키": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Bearer 토큰": re.compile(r"(?i)" + _B + r"bearer(?:\s|\\[nrt])+[A-Za-z0-9._~+/-]{16,}"),
    "인증 필드": re.compile(
        _Q + r"(?:[A-Za-z0-9]+_)*(access_token|refresh_token|id_token|api_key|account_id)"
        + _Q + r"\s*:"
    ),
    "계정 식별자": re.compile(
        _Q + r"(?:[A-Za-z0-9]+_)*user_id" + _Q + r"\s*:\s*" + _Q
        + rf"(?:user-[A-Za-z0-9]{{24}}|{_UUID})"
    ),
    "OpenAI 사용자 ID": re.compile(_B + r"user-[A-Za-z0-9]{24}(?![A-Za-z0-9])"),
    "이메일": re.compile(
        r"(?<!\\)[A-Za-z0-9._%+-]+@"
        r"(?!(?i:example\.(?:com|org|net)|[\w-]+\.(?:test|invalid|example))\b)"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"
    ),
    "가리지 못한 홈 경로": re.compile(r"/Users/(?!Shared(?:/|\b))[^/\s\"'\\]+"),
}
"""[실측 · 1·2단계 기록] 가린 뒤 0건 - Homebrew 경로의 python@3.14 는 이메일이 아니다.
이메일의 로컬 부분은 백슬래시 바로 뒤에서 시작하지 않는다 - `\\n@contextlib.contextmanager` 는
데코레이터다."""


def mask(text: str) -> str:
    for pattern, to in MASKS:
        text = pattern.sub(to, text)
    return text


def records(root: Path) -> list[tuple[str, str]]:
    """(기록 폴더 안의 경로, 가린 글) - 경로 순. 글이 아닌 파일 · 빈 기록은 거절한다.

    🔴 훑을 파일이 없으면 「0건」이 깨끗하다는 뜻이 아니다 - 폴더 이름의 오타 · 파일 하나를 넘긴
       것 · 아직 돌지 않은 감사가 빈 묶음을 「감사 기록」으로 공개한다.
    """
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
    if not out:
        raise ValueError(f"{root} 에 훑을 파일이 없다 (폴더가 아니거나 비었다) - 공개하지 않는다")
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
    """훑고, 아무것도 없을 때만 쓴다 - 묶음을 전부 임시 파일에 쓴 뒤에 이름을 바꾼다."""
    names = [root.name for root in roots]
    if len(set(names)) != len(names):
        raise ValueError(f"이름이 같은 기록 폴더가 있다 - 묶음이 서로 덮는다: {names}")
    bundles = {root: records(root) for root in roots}
    found = [f for root, rows in bundles.items() for f in findings(root, rows)]
    if found or out is None:
        return found
    out.mkdir(parents=True, exist_ok=True)
    targets = {root: out / f"{root.name}.jsonl" for root in roots}
    if blocked := [t.name for t in targets.values() if t.exists() and not t.is_file()]:
        raise ValueError(f"{out} 에 파일이 아닌 같은 이름이 있다 - 쓰지 않았다: {blocked}")
    staged: list[tuple[Path, Path]] = []
    try:
        for root, rows in bundles.items():
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=out, delete=False, suffix=".tmp"
            ) as tmp:
                staged.append((Path(tmp.name), targets[root]))
                tmp.write("".join(
                    json.dumps({"path": rel, "text": text}, ensure_ascii=False) + "\n"
                    for rel, text in rows
                ))
        for tmp_path, target in staged:
            tmp_path.replace(target)
    finally:
        for tmp_path, _ in staged:
            tmp_path.unlink(missing_ok=True)
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
