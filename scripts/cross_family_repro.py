"""교차 패밀리 감사 지적의 재현 스크립트를 돌린다 — 판정의 첫 칸 (DESIGN §9 의 5).

    python scripts/cross_family_repro.py <출력 디렉터리> <쌍 접두사...>

<출력 디렉터리> 는 `scripts/cross-family-audit.sh` 의 것이다 — `<id>.last.json` 의 지적마다
`<출력 디렉터리>/repro/<id>-<n>/` 에 decoy.py 사본과 그 지적의 repro 를 두고 돌린다. 마지막 줄이
REPRODUCED 면 「재현」이다. 위협 모델 안인지, 실행이 결함을 실제로 보였는지는 사람이 본다
(`verdicts.jsonl` — 확률을 계산만 하는 스크립트도 REPRODUCED 를 찍는다 · D125).

🔴 모델이 쓴 코드를 이 기계에서 실행한다 — 돌리기 전에 읽는다. 프롬프트가 네트워크 · 외부 프로그램 ·
   작업 디렉터리 밖 쓰기를 금하지만 강제하지는 못한다.
🔴 상자에는 decoy.py 하나만 둔다 — 재현은 decoy 의 안전 주장을 깨야 한다
   (twin · proof 를 넣지 않는다).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TIMEOUT_S = 90  # 프롬프트가 약속한 60초에 여유를 둔다
MARK = "REPRODUCED"


def _one(box: Path, decoy: Path, repro: str) -> tuple[str, str]:
    if box.exists():
        shutil.rmtree(box)
    box.mkdir(parents=True)
    shutil.copy(decoy, box / "decoy.py")
    (box / "repro.py").write_text(repro, encoding="utf-8")
    try:
        done = subprocess.run(
            [sys.executable, "-E", "-s", "repro.py"],
            cwd=box, capture_output=True, text=True, timeout=TIMEOUT_S, check=False,
        )
    except subprocess.TimeoutExpired:
        return "재현 안 됨", f"{TIMEOUT_S}초 초과"
    out = [line for line in done.stdout.split("\n") if line.strip()]
    verdict = "재현" if out and out[-1].strip() == MARK else "재현 안 됨"
    detail = f"rc={done.returncode} 마지막 줄={out[-1][:60] if out else '(없음)'}"
    if done.returncode != 0 and done.stderr.strip():
        detail += f" · stderr={done.stderr.strip().splitlines()[-1][:120]}"
    return verdict, detail


def run(out_dir: Path, pid: str) -> list[str]:
    last = out_dir / f"{pid}.last.json"
    if not last.exists():
        return [f"{pid} | - | 결과 없음"]
    pair = next((REPO / "corpus" / "decoys").glob(f"{pid}-*"))
    try:
        findings = json.loads(last.read_text(encoding="utf-8"))["findings"]
    except (json.JSONDecodeError, KeyError) as exc:
        return [f"{pid} | - | 출력 깨짐 | {exc!r}"]
    if not findings:
        return [f"{pid} | - | 지적 없음"]
    rows = []
    for n, finding in enumerate(findings, 1):
        box = out_dir / "repro" / f"{pid}-{n}"
        verdict, detail = _one(box, pair / "decoy.py", finding["repro"])
        (box / "result.txt").write_text(f"{verdict}\n{detail}\n", encoding="utf-8")
        rows.append(f"{pid} | {n}:{finding['kind']} | {verdict} | 줄 {finding['lines']} · {detail}")
    return rows


if __name__ == "__main__":
    target = Path(sys.argv[1])
    for prefix in sys.argv[2:]:
        print("\n".join(run(target, prefix)))
