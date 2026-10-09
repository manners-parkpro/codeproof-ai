"""codex 가 쓴 쌍을 코퍼스로 옮긴다 - DESIGN §7.10d 「측정」 앞 (복사만 · 모델 없이).

    uv run python scripts/xauthor_move.py --check   고를 쌍만 보인다 (쓰지 않는다)
    uv run python scripts/xauthor_move.py           corpus/xauthor/codex/ 에 복사한다
                                                    (출처는 results/xauthor/moved.json)

고르는 규칙 (선언 「2단계」): 2단계가 끝났고 (summary.json) 바퀴 2~8 을 모두 받아들인
분류마다 - 1단계에서 받아들인 쌍 하나와 바퀴마다 받아들인 쌍 하나, 8쌍. 그런 분류가 8 미만이면
「미완」이라 옮기지 않는다.

🔴 claude 는 측정 전에 쌍 내용에 관여하지 않는다 - 저자가 남긴 final/ 의 쌍 파일 다섯만
   바이트 그대로 복사한다. 덧붙은 메모 · __pycache__ 는 작성 기록에 남는다.
🔴 옮기기는 한 번이다 - 쌍이 있는 코퍼스에는 쓰지 않는다. 임시 폴더에 다 쓴 뒤 이름을 바꾼다.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from codeproof_ai.corpus.decoy import pair_dirs as corpus_pairs
from codeproof_ai.eval import crossauthor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xauthor_run as xr

REPO = xr.REPO
STAGE1 = REPO / "runs" / "xauthor" / "stage1"
STAGE2 = REPO / "runs" / "xauthor" / "stage2"
TARGET = REPO / "corpus" / "xauthor" / "codex"
MANIFEST = REPO / "results" / "xauthor" / "moved.json"
MIN_KINDS = crossauthor.MIN_KINDS
ROUNDS = range(1, 2 + xr.ROUNDS)
"""1단계가 바퀴 1, 2단계가 2~8 - 분류마다 crossauthor.PAIRS_PER_KIND 쌍이다."""
Stop = xr.Stop


def complete_kinds(stage2: Path) -> list[str]:
    """바퀴 2~8 을 모두 받아들인 분류 - 실행기 요약의 complete_kinds 와 같은 규칙 (`alive`)."""
    kinds = xr._load(stage2 / "RUN.json")["kinds"]
    return [k for k in kinds if xr.alive(k, 2 + xr.ROUNDS, stage2)]


def select(stage1: Path, stage2: Path) -> dict[str, list[Path]]:
    """분류마다 받아들인 쌍의 기록을 바퀴 순으로 - 선언과 다르면 멈춘다 (「미완」)."""
    if not (stage2 / "summary.json").is_file():
        why = "2단계가 끝나지 않았다 - summary.json 이 없다 (끝났는지 「미완」인지 본다)"
        raise Stop(xr.HUMAN, why)
    kinds = complete_kinds(stage2)
    if len(kinds) < MIN_KINDS:
        raise Stop(xr.STOP, f"8쌍을 채운 분류가 {len(kinds)}개다 - {MIN_KINDS} 미만이라 「미완」")
    records = [*xr.pair_dirs(stage1), *xr.pair_dirs(stage2)]
    chosen: dict[str, list[Path]] = {}
    for kind in kinds:
        mine = [d for d in records if xr.pair_kind(d) == kind and xr.outcome_of(d) == "accepted"]
        mine.sort(key=xr.pair_round)
        if [xr.pair_round(d) for d in mine] != list(ROUNDS):
            got = [xr.pair_round(d) for d in mine]
            raise Stop(xr.HUMAN, f"{kind} 의 받아들인 쌍이 바퀴마다 하나가 아니다: {got}")
        chosen[kind] = mine
    return chosen


def source(record: Path) -> Path:
    """기록의 final/ 에 저자가 남긴 쌍 폴더 - 하나여야 하고 쌍 파일이 다 있어야 한다."""
    found = sorted((record / "final").glob(f"{record.name}-*"))
    if len(found) != 1 or not all((found[0] / f).is_file() for f in xr.PAIR_FILES):
        raise Stop(xr.HUMAN, f"{record} 의 final/ 에 온전한 쌍 폴더가 하나가 아니다: {found}")
    return found[0]


def move(chosen: dict[str, list[Path]], target: Path, manifest: Path) -> list[dict[str, Any]]:
    """쌍 파일만 복사하고 해시를 대조한다 - 다 쓴 뒤에 이름을 바꾼다."""
    if target.exists() and any(target.iterdir()):
        raise Stop(xr.HUMAN, f"{target} 가 비어 있지 않다 - 옮기기는 한 번이다")
    tmp = target.with_name(f".{target.name}.moving")
    shutil.rmtree(tmp, ignore_errors=True)
    rows = []
    for kind, records in chosen.items():
        for record in records:
            src = source(record)
            dest = tmp / src.name
            dest.mkdir(parents=True)
            files = {}
            for name in xr.PAIR_FILES:
                shutil.copyfile(src / name, dest / name)
                files[name] = xr._sha256(dest / name)
                if files[name] != xr._sha256(src / name):
                    raise Stop(xr.HUMAN, f"{dest / name} 가 원본과 다르다")
            rows.append({
                "pair": src.name, "kind": kind, "round": xr.pair_round(record),
                "record": f"{record.parent.name}/{record.name}", "files": files,
            })
    if target.exists():
        target.rmdir()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp.rename(target)
    xr._json(manifest, {
        "what": "DESIGN §7.10d - codex 가 쓴 쌍을 코퍼스로 (scripts/xauthor_move.py · 복사만)",
        "pairs": rows,
    })
    return rows


def main(argv: list[str]) -> int:
    if argv not in ([], ["--check"]):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        chosen = select(STAGE1, STAGE2)
        for kind, records in chosen.items():
            print(f"{kind}: " + " · ".join(f"{d.parent.name}/{d.name}" for d in records))
        if argv:
            return xr.DONE
        rows = move(chosen, TARGET, MANIFEST)
    except Stop as stop:
        print(f"rc={stop.rc} · {stop}", file=sys.stderr)
        return stop.rc
    print(f"{len(rows)}쌍 = 분류 {len(chosen)} x {len(rows) // len(chosen)} → {TARGET}")
    print(f"코퍼스의 쌍 {len(corpus_pairs(TARGET))}개")
    return xr.DONE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
