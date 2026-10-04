"""교차 패밀리 감사의 프롬프트 — 머리말 뒤에 쌍의 파일 넷을 줄 번호와 함께 붙인다 (DESIGN §9 의 5).

    python scripts/cross_family_prompt.py <쌍 디렉터리> <머리말 파일>

결과 디렉터리(`results/cross-family-*/findings.jsonl`)의 `prompt_sha256` 은 이 출력의 sha256 이다
(끝 줄바꿈 없음). 실행기는 `scripts/cross-family-audit.sh` 다.

🔴 꼴을 바꾸면 다른 측정이다 — 줄 번호 폭 · 구분 줄 · 파일 순서 · 빈 줄 하나까지
   프롬프트 해시에 든다.
"""

from __future__ import annotations

import sys
from pathlib import Path

FILES = ("meta.toml", "decoy.py", "twin.py", "proof.py")


def build(pair: Path, head: str) -> str:
    parts = [head]
    for name in FILES:
        lines = (pair / name).read_text(encoding="utf-8").split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        numbered = "\n".join(f"{i:4d} | {line}" for i, line in enumerate(lines, 1))
        parts.append(f"=== {name} (줄 번호 | 내용) ===\n{numbered}")
    return "\n\n".join(parts)


if __name__ == "__main__":
    pair_dir, head_file = Path(sys.argv[1]), Path(sys.argv[2])
    sys.stdout.write(build(pair_dir, head_file.read_text(encoding="utf-8")))
