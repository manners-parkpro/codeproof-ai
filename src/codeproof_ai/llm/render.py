"""프롬프트 조립 - 양 벤더 공통.

🔴 nonce 는 **맨 앞**에 붙인다 (CLAUDE.md L3).
   캐싱은 prefix 매칭이므로 뒤에 붙이면 아무 효과가 없다.
   OpenAI 는 캐싱이 기본 활성화라 무력화하지 않으면
   2회차부터 추론이 아니라 prefill 생략을 재게 된다.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeproof_ai.domain.target import ReviewTarget

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str = "review_v1") -> str:
    """프롬프트를 파일에서 읽는다.

    🔴 프롬프트는 코드가 아니라 **데이터**다. 파이썬 문자열 리터럴로
       인라인하면 버전 추적이 불가능해진다.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        msg = f"프롬프트가 없다: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def prompt_hash(text: str) -> str:
    """RunManifest 에 실리는 프롬프트 해시."""
    return hashlib.blake2b(text.encode("utf-8"), digest_size=12).hexdigest()


def render_target(target: ReviewTarget) -> str:
    """리뷰 대상을 사용자 메시지 본문으로 만든다.

    파일 내용에 **1-based 줄 번호를 붙인다.** 모델이 line_start/line_end 를
    돌려줘야 하는데, 번호 없이 세게 하면 오프바이원이 측정 노이즈가 된다.
    """
    blocks: list[str] = []
    for f in target.files:
        numbered = "\n".join(
            f"{i:>4} | {line}" for i, line in enumerate(f.content.splitlines(), start=1)
        )
        blocks.append(f"### {f.path}\n\n```\n{numbered}\n```")

    parts = ["## Files under review", "", *blocks]
    if target.diff is not None:
        parts += ["", "## Diff", "", "```diff", target.diff, "```"]
    return "\n".join(parts)


def render_user_message(target: ReviewTarget, nonce: str | None) -> str:
    """nonce + 대상. nonce 가 있으면 반드시 맨 앞이다."""
    body = render_target(target)
    if nonce is None:
        return body
    return f"<!-- run-nonce: {nonce} -->\n\n{body}"
