"""저장소의 코퍼스 디렉터리 - 쌍마다 도는 테스트가 같은 목록을 쓴다.

검증기 · 반증 · 변이 · docstring 형식 · 린트 제외 테스트가 이 목록을 돈다 (DESIGN §7.10d
「수집 전에 준비할 것」 ②). 🔴 목록을 테스트 파일마다 따로 두지 않는다 - 새 코퍼스를 한
파일에만 더하면 나머지 테스트는 그 코퍼스를 조용히 건너뛴다.

쌍을 찾는 규칙은 `codeproof_ai.corpus.decoy.pair_dirs` 하나다. 없는 코퍼스는 빈 목록이다.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DECOYS = REPO / "corpus" / "decoys"
"""목표 150쌍 코퍼스 - claude 가 썼다."""

CORPORA = (DECOYS, REPO / "corpus" / "xauthor" / "codex")
"""쌍 단위 규격 테스트가 도는 코퍼스 전부. 두 번째는 codex 가 쓴 쌍이다 (DESIGN §7.10d)."""
