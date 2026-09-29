"""코퍼스를 **에이전트가 리뷰할 수 있는 형태**로 내보낸다.

🔴 왜 필요한가.

`ReviewerKind.AGENT` 는 처음부터 설계에 있었고 `import --kind agent` 도
구현돼 있었는데, **코퍼스를 에이전트에게 먹이는 방법이 없었다.** 그래서
모델 비교 축이 비어 있었다 - 재료가 다 있는데 연결선 하나가 없던 것이다.

## 에이전트는 model_api 와 조건이 다르다 (A2)

그래서 주는 것도 다르다:

    model_api  번호 붙은 코드를 **메시지 본문으로** 받는다 (render_target)
    agent      **진짜 파일**을 받고 자기 툴로 읽는다 - 탐색·다회 턴이 가능하다

같게 맞추면 에이전트를 model_api 처럼 쓰는 것이라 층을 나눈 의미가 없다.
🔴 다만 **채점과 집계는 같은 하네스**를 탄다. 조건이 다른 것과 채점이 다른
   것은 별개다 - `ReviewerKind` 가 섞이지 않게 막는다.

## 🔴 가시 범위는 분석기와 똑같이 묶는다 (C1)

`materialize()` 가 분석기를 임시 디렉터리에 가두는 것과 같은 이유로,
에이전트도 **자기 샘플 파일 하나만** 보는 곳에서 돌아야 한다. 실제 코퍼스
디렉터리에서 돌리면 옆 decoy 와 `meta.toml`(정답!)이 보인다.

여기서는 평평하게 내보내고, **격리는 실행기(`scripts/review-with-agent.sh`)가**
샘플마다 새 임시 디렉터리에 복사해서 만든다. 내보내기가 격리까지 하면
디렉터리 구조 자체가 계약이 되어 실행기를 바꾸기 어려워진다.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from codeproof_ai.domain.finding import Category, Severity
from codeproof_ai.llm.render import load_prompt, prompt_hash

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from codeproof_ai.eval.sample import LabeledSample

SCHEMA_VERSION = 1
PROMPT_FILE = "PROMPT.md"
MANIFEST_FILE = "MANIFEST.json"


def _output_contract() -> str:
    """에이전트가 맞춰야 할 출력 규격.

    🔴 열거값을 하드코딩하지 않는다 - 도메인 enum 에서 뽑는다. 손으로 적으면
       값이 늘었을 때 조용히 낡고, 그러면 파서가 전부 `other` 로 접는다.
    """
    cats = " | ".join(c.value for c in Category)
    sevs = " | ".join(s.value for s in Severity)
    return f"""
## Output

Return ONLY a JSON object. No prose, no markdown fence, no explanation.

{{"findings": [
  {{"file": "<filename in this directory>",
   "line_start": <int>, "line_end": <int>,
   "category": "<one of below>", "severity": "<one of below>",
   "message": "<what fails, and the input or state that makes it fail>"}}
]}}

category: {cats}
severity: {sevs}

Line numbers are 1-based and refer to the file as it exists in this directory.
If there is no substantiable defect, return exactly {{"findings": []}}.
"""


def build_prompt(prompt_name: str = "review_v1") -> str:
    """리뷰 지시 + 출력 규격.

    🔴 리뷰 지시는 `model_api` 와 **같은 파일**을 쓴다. 다른 프롬프트를 주면
       층 차이가 아니라 프롬프트 차이를 재게 된다 - 프롬프트만으로 정확도가
       최대 76 포인트 움직인다는 것이 이미 측정돼 있다.
    """
    return load_prompt(prompt_name) + _output_contract()


def export_for_agent(
    samples: Sequence[LabeledSample],
    out_dir: Path,
    *,
    prompt_name: str = "review_v1",
) -> dict[str, object]:
    """샘플마다 디렉터리 하나 + 공통 프롬프트를 쓴다.

    Returns:
        매니페스트 (호출부가 그대로 출력해도 되는 형태)
    """
    prompt = build_prompt(prompt_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / PROMPT_FILE).write_text(prompt, encoding="utf-8")

    written: list[dict[str, object]] = []
    for s in samples:
        box = out_dir / s.sample_id
        box.mkdir(parents=True, exist_ok=True)
        for f in s.target.files:
            dest = box / f.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f.content, encoding="utf-8")
        written.append(
            {"sample_id": s.sample_id, "files": [f.path for f in s.target.files]}
        )

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "prompt": PROMPT_FILE,
        "prompt_name": prompt_name,
        # 🔴 이 해시가 model_api 실행의 prompt_hash 와 같아야 같은 과제다.
        "prompt_hash": prompt_hash(prompt),
        "samples": written,
    }
    (out_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
