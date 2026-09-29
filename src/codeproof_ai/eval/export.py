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

## 🔴 출력 규격은 model_api 의 스키마에서 뽑는다

[실측] 규격을 손으로 적었을 때 `quoted_code` · `failure_mode` 가 빠져 있었다.
리뷰 지시는 「`quoted_code` 에 원문을 인용하라」고 하는데 규격에는 그 칸이
없었다 - **지시끼리 모순**이다. 인용이 없으면 LLM 지적의 지문이
`(category, 파일, "")` 로 수렴해 같은 파일의 서로 다른 지적이 하나로 뭉친다
(D005#twin: 서로 다른 결함 2건 → 관측 1건).

→ 규격 문장도, 실행기가 CLI 에 강제하는 `SCHEMA.json` 도 `review_schema()`
  하나에서 나온다. model_api 가 벤더 API 에 보내는 바로 그 스키마다.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from codeproof_ai.llm.render import load_prompt, prompt_hash
from codeproof_ai.llm.schema import review_schema

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from codeproof_ai.eval.sample import LabeledSample

SCHEMA_VERSION = 2
PROMPT_FILE = "PROMPT.md"
SCHEMA_FILE = "SCHEMA.json"
MANIFEST_FILE = "MANIFEST.json"


def _placeholder(spec: Mapping[str, Any]) -> str:
    if "enum" in spec:
        return '"<one of below>"'
    if spec.get("type") == "integer":
        return "<int>"
    return '"<string>"'


def _output_contract(schema: Mapping[str, Any]) -> str:
    """에이전트가 맞춰야 할 출력 규격 - **스키마에서 뽑는다.**

    🔴 칸 이름도 열거값도 손으로 적지 않는다. 손으로 적은 목록은 조용히 낡는다 -
       칸이 빠진 채로 몇 주를 갔다 (모듈 docstring). 칸의 뜻은 스키마의
       `description` 이 싣고, 실행기가 같은 스키마를 CLI 에 강제한다.
    """
    item = schema["properties"]["findings"]["items"]
    props = item["properties"]
    names = item["required"]
    fields = ",\n   ".join(f'"{n}": {_placeholder(props[n])}' for n in names)
    enums = "\n".join(
        f"{n}: {' | '.join(props[n]['enum'])}" for n in names if "enum" in props[n]
    )
    return f"""
## Output

Return ONLY a JSON object. No prose, no markdown fence, no explanation.

{{"findings": [
  {{{fields}}}
]}}

{enums}

Line numbers are 1-based and refer to the file as it exists in this directory.
If there is no substantiable defect, return exactly {{"findings": []}}.
"""


def _files_section(samples: Sequence[LabeledSample]) -> str:
    """리뷰 지시가 말하는 「아래에 나열된 파일」을 실제로 나열한다.

    지시(`review_v1`)는 model_api 와 공유하므로 "every file listed below" 라고
    쓴다. model_api 는 그 아래에 파일 본문이 붙지만 에이전트는 아니다 -
    나열하지 않으면 지시가 가리키는 대상이 없다.

    🔴 프롬프트는 전 샘플 공통이므로 제시 파일 목록도 같아야 한다. 다르면
       한 프롬프트로 「아래 파일」을 말할 수 없으니 거부한다.
    """
    listings = {tuple(f.path for f in s.target.files) for s in samples}
    if len(listings) != 1:
        msg = (
            "샘플마다 제시 파일 목록이 다르다 - 공통 프롬프트 하나로는 "
            f"「아래 파일」을 말할 수 없다: {sorted(listings)[:3]}"
        )
        raise ValueError(msg)
    (paths,) = listings
    listed = "\n".join(f"- {p}" for p in paths)
    return f"\n## Files\n\n{listed}\n\nThey are in the current working directory.\n"


def build_prompt(
    samples: Sequence[LabeledSample], prompt_name: str = "review_v1"
) -> str:
    """리뷰 지시 + 파일 목록 + 출력 규격.

    🔴 리뷰 지시는 `model_api` 와 **같은 파일**을 쓴다. 다른 프롬프트를 주면
       층 차이가 아니라 프롬프트 차이를 재게 된다 - 프롬프트만으로 정확도가
       최대 76 포인트 움직인다는 것이 이미 측정돼 있다.
    """
    return (
        load_prompt(prompt_name)
        + _files_section(samples)
        + _output_contract(review_schema())
    )


def schema_text() -> str:
    """실행기가 CLI 에 강제할 스키마. 해시가 안정되도록 키를 정렬한다."""
    return json.dumps(review_schema(), ensure_ascii=False, indent=2, sort_keys=True)


def export_for_agent(
    samples: Sequence[LabeledSample],
    out_dir: Path,
    *,
    prompt_name: str = "review_v1",
) -> dict[str, object]:
    """샘플마다 디렉터리 하나 + 공통 프롬프트 + 출력 스키마를 쓴다.

    Returns:
        매니페스트 (호출부가 그대로 출력해도 되는 형태)
    """
    prompt = build_prompt(samples, prompt_name)
    schema = schema_text()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / PROMPT_FILE).write_text(prompt, encoding="utf-8")
    (out_dir / SCHEMA_FILE).write_text(schema + "\n", encoding="utf-8")

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
        # 🔴 해시가 둘인 이유. model_api 의 prompt_hash 는 **지시만** 해싱한다
        #    (cli 의 `prompt_hash_of(load_prompt())`). 전에는 여기 「이 해시가
        #    model_api 의 것과 같아야 같은 과제」라고 적고 지시+규격을 해싱해서
        #    **구조적으로 항상 달랐다.** 비교용과 재현용을 나눈다.
        "instruction_hash": prompt_hash(load_prompt(prompt_name)),  # model_api 와 비교
        "prompt_hash": prompt_hash(prompt),  # 에이전트가 실제로 받은 전문
        "schema": SCHEMA_FILE,
        "schema_hash": prompt_hash(schema),
        "samples": written,
    }
    (out_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
